"""
对话服务 - AI对话核心逻辑
T-015: SSE流式对话 + 消息存储 + 引用来源
T-017: AI降级处理
"""

import uuid
import json
import time
import logging
from typing import Optional, AsyncIterator

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.adapters.ragflow_client import ragflow_client
from app.adapters.content_filter import filter_content
from app.core.config import settings
from app.models import Session, Message, MessageRole, User
from app.services.team_service import TeamService

logger = logging.getLogger(__name__)

# 推荐问题（初始版本硬编码，后续可从数据库加载）
DEFAULT_SUGGESTIONS = [
    "如何查询客户的出货记录？",
    "退货流程是怎样的？",
    "如何申请价格折扣？",
    "出口到欧洲需要什么认证？",
    "新客户信用审核流程是什么？",
]

FALLBACK_MESSAGE = "🔍 抱歉，暂时无法获取回答，请稍后重试或联系管理员。"

# RAGFlow 未找到答案时的英文回复模式（用于检测并替换为中文）
NOT_FOUND_PATTERNS = [
    "not found in the knowledge base",
    "is not found in",
    "no relevant information",
    "cannot find the answer",
    "unable to find",
    "don't have enough information",
    "no answer found",
]

NOT_FOUND_MESSAGE = (
    "😔 很抱歉，知识库中暂未找到与您问题相关的内容。\n\n"
    "您可以尝试：\n"
    "1. 换个方式描述您的问题\n"
    "2. 使用更具体的关键词\n"
    "3. 点击下方 **🙋 转人工** 按钮，由人工客服为您解答"
)


def _is_not_found_response(text: str) -> bool:
    """检测 RAGFlow 返回的内容是否为「未找到答案」的回复"""
    lower = text.lower().strip()
    return any(pattern in lower for pattern in NOT_FOUND_PATTERNS)


def _has_no_retrieval_chunks(reference: dict | None) -> bool:
    """检测 RAGFlow 是否没有检索到任何知识片段"""
    if reference is None:
        return True
    if not isinstance(reference, dict):
        return True
    chunks = reference.get("chunks", [])
    return len(chunks) == 0


class ChatService:
    """对话服务 - 应用层"""

    # ========== Session CRUD ==========

    @staticmethod
    async def create_session(
        db: AsyncSession, user: User, title: str = "新对话"
    ) -> Session:
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user.id,
            team_id=user.active_team_id,
            title=title,
        )
        db.add(session)
        await db.flush()
        return session

    @staticmethod
    async def list_sessions(
        db: AsyncSession, user: User, page: int = 1, page_size: int = 20
    ) -> tuple[list[Session], int]:
        query = (
            select(Session)
            .where(Session.user_id == user.id, Session.is_active == True)
            .order_by(Session.updated_at.desc())
        )
        count = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar() or 0
        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        return list(result.scalars().all()), count

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: str, user: User) -> bool:
        result = await db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user.id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("会话不存在")
        session.is_active = False
        await db.flush()
        return True

    # ========== Messages ==========

    @staticmethod
    async def get_history(
        db: AsyncSession, session_id: str, user: User
    ) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id, Message.user_id == user.id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def search_messages(
        db: AsyncSession, user: User, keyword: str
    ) -> list[Message]:
        """搜索用户的历史消息（按内容模糊匹配）"""
        result = await db.execute(
            select(Message)
            .join(Session, Message.session_id == Session.id)
            .where(
                Message.user_id == user.id,
                Session.is_active == True,
                Message.content.ilike(f"%{keyword}%"),
            )
            .order_by(Message.created_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())

    @staticmethod
    async def send_message_stream(
        db: AsyncSession, session_id: str, user: User, content: str,
        thinking: bool = False,
    ) -> AsyncIterator[str]:
        """
        发送消息并返回SSE流
        流程: 用户消息存储 → RAGflow SSE → 内容过滤 → 流式返回 → AI消息存储
        FR-39: 支持 thinking 参数
        """
        t_start = time.monotonic()
        timing = {}  # 各环节耗时(秒)

        # 1. 存储用户消息
        user_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user.id,
            role=MessageRole.USER,
            content=content,
        )
        db.add(user_msg)
        await db.flush()
        timing["save_user_msg"] = round(time.monotonic() - t_start, 3)

        # 2. 获取session信息
        t2 = time.monotonic()
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            yield f"data: {json.dumps({'error': '会话不存在'})}\n\n"
            return

        # 3. 调用RAGflow SSE (带降级)
        ai_answer = ""
        citations = None
        ragflow_request_body = None  # 记录请求体
        ragflow_raw_reference = None  # 记录原始响应引用
        chat_id = ""
        rag_session_id = ""
        is_filtered = False  # 内容过滤标志
        is_fallback = False  # 降级标志

        t_sse = time.monotonic()  # 初始化，防止 finally 中 NameError
        try:
            # 如果没有RAGflow conversation ID，创建一个
            if not session.ragflow_conversation_id:
                # 从团队配置获取助手ID
                target_assistant_id = None
                if user.active_team_id:
                    target_assistant_id = await TeamService.get_team_assistant_id(db, user.active_team_id)

                if target_assistant_id:
                    assistants_list = [type('obj', (object,), {'id': target_assistant_id})()]
                else:
                    assistants_list = await ragflow_client.list_chat_assistants()

                if not assistants_list:
                    yield f"data: {json.dumps({'error': '当前团队未配置对话助手，请联系IT管理员绑定'})}\n\n"
                    return

                rag_session = await ragflow_client.create_session(
                    assistants_list[0].id, session.title
                )
                session.ragflow_conversation_id = f"{assistants_list[0].id}:{rag_session.id}"
                await db.flush()

            chat_id, rag_session_id = session.ragflow_conversation_id.split(":", 1)
            timing["session_init"] = round(time.monotonic() - t2, 3)

            # 记录 RAGFlow 请求体
            ragflow_request_body = {
                "url": f"/chats/{chat_id}/completions",
                "method": "POST",
                "body": {
                    "question": content,
                    "session_id": rag_session_id,
                    "stream": True,
                    **(({"enable_thinking": True}) if thinking else {}),
                },
            }

            t_sse = time.monotonic()
            t_first_token = None
            # FR-39: 使用 RAGFlow 的 start_to_think / end_to_think 标记
            in_think_block = False  # 是否正在接收思考内容
            think_content = ""  # 累积的思考内容

            async for chunk in ragflow_client.completion_stream(
                chat_id, rag_session_id, content, thinking=thinking,
            ):
                if chunk.is_final:
                    if chunk.reference:
                        citations = chunk.reference
                        ragflow_raw_reference = chunk.reference
                    # FR-39: 流结束时，如果还在思考中，发送结束标记
                    if in_think_block and think_content:
                        yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                    # done 事件延迟到 AI 消息存储后发送（携带真实 message_id）
                    break

                # 内容过滤
                filtered_text, was_filtered = filter_content(chunk.answer)
                if was_filtered:
                    ai_answer = filtered_text
                    is_filtered = True
                    yield f"data: {json.dumps({'type': 'content', 'content': filtered_text})}\n\n"
                    break

                if t_first_token is None and chunk.answer:
                    t_first_token = time.monotonic()
                    timing["first_token"] = round(t_first_token - t_sse, 3)

                # FR-39: 基于 RAGFlow start_to_think / end_to_think 字段分离思考内容和正文
                if chunk.start_to_think:
                    in_think_block = True
                    # 发送思考内容（start_to_think 的 chunk 也可能携带 answer）
                    if chunk.answer:
                        think_content += chunk.answer
                        yield f"data: {json.dumps({'type': 'thinking', 'content': chunk.answer})}\n\n"
                    continue

                if chunk.end_to_think:
                    in_think_block = False
                    # end_to_think 的 chunk 也可能携带最后一段思考内容
                    if chunk.answer:
                        think_content += chunk.answer
                        yield f"data: {json.dumps({'type': 'thinking', 'content': chunk.answer})}\n\n"
                    yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                    continue

                raw = chunk.answer
                if in_think_block:
                    # 思考阶段：所有 answer 都作为思考内容发送
                    if raw:
                        think_content += raw
                        yield f"data: {json.dumps({'type': 'thinking', 'content': raw})}\n\n"
                else:
                    # 普通正文
                    if raw:
                        ai_answer += raw
                        yield f"data: {json.dumps({'type': 'content', 'content': raw})}\n\n"

        except Exception as e:
            logger.error(f"RAGflow error [{type(e).__name__}]: {e}")
            is_fallback = True
            if not ai_answer.strip():
                ai_answer = FALLBACK_MESSAGE
                yield f"data: {json.dumps({'type': 'content', 'content': FALLBACK_MESSAGE})}\n\n"
        finally:
            timing["sse_stream"] = round(time.monotonic() - t_sse, 3)

        # 3.45 回填 reference（SSE 流未携带 或 chunks 为空时，从 RAGFlow 会话历史 API 获取）
        t_backfill = time.monotonic()
        need_backfill = _has_no_retrieval_chunks(ragflow_raw_reference)
        logger.info(f"Reference 回填检查: ragflow_raw_reference={'None' if ragflow_raw_reference is None else 'has_data'}, "
                     f"need_backfill={need_backfill}, chat_id={chat_id}, rag_session_id={rag_session_id}")
        if need_backfill and chat_id and rag_session_id:
            try:
                rag_messages = await ragflow_client.get_session_messages(chat_id, rag_session_id)
                logger.info(f"RAGFlow 会话历史返回 {len(rag_messages)} 条消息")
                # 取最后一条 assistant 消息的 reference
                for msg in reversed(rag_messages):
                    role = msg.get("role", "")
                    has_ref = bool(msg.get("reference"))
                    logger.debug(f"  消息 role={role}, has_reference={has_ref}")
                    if role == "assistant" and has_ref:
                        ref_data = msg["reference"]
                        # RAGFlow 会话消息中 reference 可能是列表或字典
                        if isinstance(ref_data, list) and len(ref_data) > 0:
                            ragflow_raw_reference = {"chunks": ref_data}
                        elif isinstance(ref_data, dict):
                            ragflow_raw_reference = ref_data
                        else:
                            continue
                        logger.info(f"成功从 RAGFlow 会话历史回填 reference 数据, type={type(ref_data).__name__}")
                        break
            except Exception as e:
                logger.warning(f"回填 reference 失败: {e}")
        timing["backfill"] = round(time.monotonic() - t_backfill, 3)

        # 3.5 检测「未找到」回复
        # 方式1: RAGFlow 的英文模式匹配（文本中明确说"未找到"）
        # 方式2: RAGFlow 没有检索到任何知识片段 且 回答较短（可能是默认模板）
        # 注意: 如果 AI 返回了有实质内容的回答，即使 reference 为空也不应判定为"未找到"
        text_not_found = _is_not_found_response(ai_answer)
        no_chunks = _has_no_retrieval_chunks(ragflow_raw_reference)
        # 仅当文本明确未找到，或（无检索片段 且 回答很短 / 回答为空）时判定为未找到
        is_not_found = text_not_found or (no_chunks and len(ai_answer.strip()) < 50)
        if is_not_found:
            ai_answer = NOT_FOUND_MESSAGE
            # 发送替换内容 (前端会用 replace 事件清除之前的流内容)
            yield f"data: {json.dumps({'type': 'replace', 'content': NOT_FOUND_MESSAGE, 'not_found': True})}\n\n"

        # 4. 存储AI回答 (含完整 RAGFlow 请求/响应元数据)
        t_save = time.monotonic()
        timing["total"] = round(t_save - t_start, 3)

        enriched_citations = {
            "ragflow_request": ragflow_request_body,
            "ragflow_response": {
                "answer": ai_answer or FALLBACK_MESSAGE,
                "is_not_found": is_not_found,
                "reference": ragflow_raw_reference,
            },
            "chat_id": chat_id,
            "session_id": rag_session_id,
            "timing": timing,
        }
        ai_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user.id,
            role=MessageRole.ASSISTANT,
            content=ai_answer or FALLBACK_MESSAGE,
            citations=enriched_citations,
        )
        db.add(ai_msg)
        await db.flush()
        timing["save_ai_msg"] = round(time.monotonic() - t_save, 3)
        logger.info(f"Chat timing: {timing}")

        # 6. 发送 done 事件（携带真实消息 ID，解决前端临时 ID 问题）
        done_event = {
            'type': 'done',
            'user_message_id': user_msg.id,
            'ai_message_id': ai_msg.id,
            'citations': citations,
        }
        if is_filtered:
            done_event['filtered'] = True
        if is_fallback:
            done_event['fallback'] = True
        if is_not_found:
            done_event['not_found'] = True
        yield f"data: {json.dumps(done_event)}\n\n"

        # 5. 更新session标题(如果是第一条消息)
        if session.title == "新对话" and content:
            session.title = content[:50]
            await db.flush()

    @staticmethod
    async def get_suggestions() -> list[str]:
        """获取推荐问题"""
        return DEFAULT_SUGGESTIONS

    @staticmethod
    async def search_messages(
        db: AsyncSession, user: User, keyword: str
    ) -> list[Message]:
        """搜索历史消息"""
        result = await db.execute(
            select(Message)
            .join(Session)
            .where(
                Session.user_id == user.id,
                Message.content.contains(keyword),
            )
            .order_by(Message.created_at.desc())
            .limit(20)
        )
        return list(result.scalars().all())
