"""
统计分析接口 - 7 API (T-043)
overview, trends, top-questions, roi, coverage, comparison, query-logs
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_kb_admin
from app.db.session import get_db
from app.models import (
    User, Session, Message, Feedback, FeedbackType,
    Ticket, TicketStatus, DocumentMeta, QAMeta, OperationLog,
)

router = APIRouter()


def _date_range(days: int = 7):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start, end


@router.get("/overview")
async def get_overview(
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """核心指标概览"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_docs = (await db.execute(select(func.count(DocumentMeta.id)))).scalar() or 0
    total_qa = (await db.execute(select(func.count(QAMeta.id)))).scalar() or 0
    today_sessions = (await db.execute(
        select(func.count(Session.id)).where(Session.created_at >= today_start)
    )).scalar() or 0
    today_messages = (await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= today_start)
    )).scalar() or 0
    pending_tickets = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.PENDING)
    )).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # 好评率
    total_fb = (await db.execute(select(func.count(Feedback.id)))).scalar() or 0
    like_fb = (await db.execute(
        select(func.count(Feedback.id)).where(Feedback.type == FeedbackType.LIKE)
    )).scalar() or 0
    satisfaction_rate = round(like_fb / total_fb * 100, 1) if total_fb > 0 else 0.0

    return {
        "total_documents": total_docs,
        "total_qa": total_qa,
        "today_sessions": today_sessions,
        "today_messages": today_messages,
        "pending_tickets": pending_tickets,
        "total_users": total_users,
        "satisfaction_rate": satisfaction_rate,
    }


@router.get("/trends")
async def get_trends(
    days: int = Query(7, ge=1, le=30),
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """对话趋势(按天)"""
    start, end = _date_range(days)
    result = await db.execute(
        select(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count"),
        )
        .where(Message.created_at.between(start, end))
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
    )
    return {"items": [{"date": str(r.date), "count": r.count} for r in result.all()]}


@router.get("/top-questions")
async def get_top_questions(
    limit: int = Query(10, ge=1, le=50),
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """热门问题TOP N"""
    start, _ = _date_range(30)
    result = await db.execute(
        select(Message.content, func.count(Message.id).label("count"))
        .where(
            Message.created_at >= start,
            Message.role == "user",
        )
        .group_by(Message.content)
        .order_by(func.count(Message.id).desc())
        .limit(limit)
    )
    return {"items": [{"question": r.content, "count": r.count} for r in result.all()]}


@router.get("/roi")
async def get_roi(
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """ROI指标 - AI解决率"""
    start, _ = _date_range(30)
    total_sessions = (await db.execute(
        select(func.count(Session.id)).where(Session.created_at >= start)
    )).scalar() or 0

    # 没产生工单的session视为AI自行解决
    sessions_with_ticket = (await db.execute(
        select(func.count(func.distinct(Ticket.session_id)))
        .where(Ticket.created_at >= start)
    )).scalar() or 0

    ai_resolved = total_sessions - sessions_with_ticket if total_sessions > 0 else 0
    resolution_rate = round(ai_resolved / total_sessions * 100, 1) if total_sessions > 0 else 0.0

    return {
        "total_sessions": total_sessions,
        "ai_resolved": ai_resolved,
        "human_involved": sessions_with_ticket,
        "resolution_rate": resolution_rate,
    }


@router.get("/coverage")
async def get_coverage(
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """知识覆盖率 - 有引用的回答占比"""
    start, _ = _date_range(30)
    total_ai = (await db.execute(
        select(func.count(Message.id)).where(
            Message.created_at >= start, Message.role == "assistant"
        )
    )).scalar() or 0
    with_citation = (await db.execute(
        select(func.count(Message.id)).where(
            Message.created_at >= start,
            Message.role == "assistant",
            Message.citations.isnot(None),
        )
    )).scalar() or 0

    return {
        "total_answers": total_ai,
        "with_citation": with_citation,
        "coverage_rate": round(with_citation / total_ai * 100, 1) if total_ai > 0 else 0.0,
    }


@router.get("/comparison")
async def get_comparison(
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """时段对比(本周vs上周)"""
    now = datetime.now(timezone.utc)
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)

    this_week = (await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= this_week_start)
    )).scalar() or 0
    last_week = (await db.execute(
        select(func.count(Message.id)).where(
            Message.created_at.between(last_week_start, this_week_start)
        )
    )).scalar() or 0

    change = round((this_week - last_week) / last_week * 100, 1) if last_week > 0 else 0.0

    return {
        "this_week": this_week,
        "last_week": last_week,
        "change_percent": change,
    }


@router.get("/question-logs")
async def get_question_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    feedback_type: Optional[str] = Query(None, description="all|like|dislike|favorited|transferred|no_feedback"),
    keyword: Optional[str] = Query(None),
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """提问日志 - 按反馈类型筛选"""
    from sqlalchemy.orm import aliased

    UserMsg = aliased(Message, name="user_msg")
    AiMsg = aliased(Message, name="ai_msg")

    # --- 构建基础子查询: 每条用户消息 + 配对的AI回答 ---
    # 找到每个用户消息之后的第一条AI回答
    ai_subq = (
        select(
            Message.session_id,
            Message.content.label("ai_content"),
            Message.id.label("ai_msg_id"),
            Message.created_at.label("ai_created_at"),
        )
        .where(Message.role == "assistant")
        .subquery("ai_sub")
    )

    # --- 主查询 ---
    from sqlalchemy.orm import joinedload as jl

    # T-17.1: Feedback JOIN 改用 message_id（匹配唯一约束）
    # T-17.2: 使用 DISTINCT 防止重复行
    base_query = (
        select(
            Message.id,
            Message.session_id,
            Message.user_id,
            Message.content.label("question"),
            Message.created_at,
            User.display_name.label("user_name"),
            Feedback.type.label("feedback_type_val"),
        )
        .distinct()
        .join(User, User.id == Message.user_id)
        .outerjoin(
            Feedback,
            and_(
                Feedback.message_id == Message.id,
                Feedback.user_id == Message.user_id,
            )
        )
        .where(Message.role == "user")
    )

    # --- 关键词搜索 ---
    if keyword:
        base_query = base_query.where(Message.content.contains(keyword))

    # --- 反馈类型筛选 ---
    if feedback_type and feedback_type != "all":
        if feedback_type == "like":
            base_query = base_query.where(Feedback.type == FeedbackType.LIKE)
        elif feedback_type == "dislike":
            base_query = base_query.where(Feedback.type == FeedbackType.DISLIKE)
        elif feedback_type == "favorited":
            from app.models import Favorite
            base_query = base_query.join(
                Favorite,
                and_(Favorite.user_id == Message.user_id),
            )
        elif feedback_type == "transferred":
            base_query = base_query.join(
                Ticket,
                and_(
                    Ticket.session_id == Message.session_id,
                    Ticket.source == "manual",
                ),
            )
        elif feedback_type == "no_feedback":
            base_query = base_query.where(Feedback.id.is_(None))

    # --- 总数 ---
    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # --- 分页查询 ---
    result = await db.execute(
        base_query
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()

    # --- 获取配对的AI回答 ---
    if rows:
        session_ids = list(set(r.session_id for r in rows))
        ai_result = await db.execute(
            select(Message.session_id, Message.content)
            .where(
                Message.session_id.in_(session_ids),
                Message.role == "assistant",
            )
            .order_by(Message.created_at.asc())
        )
        # 每个 session 取最新的 AI 回答
        ai_answers = {}
        for ai_row in ai_result.all():
            ai_answers[ai_row.session_id] = ai_row.content

        # 检查收藏状态
        from app.models import Favorite
        fav_result = await db.execute(
            select(Favorite.user_id, Favorite.message_id)
            .where(Favorite.message_id.in_([r.id for r in rows]))
        )
        fav_set = set((r.user_id, r.message_id) for r in fav_result.all())

        # 检查转人工状态
        ticket_result = await db.execute(
            select(func.distinct(Ticket.session_id))
            .where(
                Ticket.session_id.in_(session_ids),
                Ticket.source == "manual",
            )
        )
        transferred_sessions = set(r[0] for r in ticket_result.all())
    else:
        ai_answers = {}
        fav_set = set()
        transferred_sessions = set()

    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "user_name": r.user_name,
            "question": r.question,
            "answer": ai_answers.get(r.session_id, ""),
            "feedback_type": r.feedback_type_val.value if r.feedback_type_val else None,
            "is_favorited": (r.user_id, r.id) in fav_set,
            "is_transferred": r.session_id in transferred_sessions,
            "created_at": r.created_at.isoformat(),
        })

    # --- 汇总统计 ---
    all_user_msgs = select(func.count(Message.id)).where(Message.role == "user")
    stats_total = (await db.execute(all_user_msgs)).scalar() or 0

    stats_liked = (await db.execute(
        select(func.count(Feedback.id)).where(Feedback.type == FeedbackType.LIKE)
    )).scalar() or 0

    stats_disliked = (await db.execute(
        select(func.count(Feedback.id)).where(Feedback.type == FeedbackType.DISLIKE)
    )).scalar() or 0

    from app.models import Favorite
    stats_favorited = (await db.execute(
        select(func.count(Favorite.id))
    )).scalar() or 0

    stats_transferred = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.source == "manual")
    )).scalar() or 0

    return {
        "items": items,
        "total": total,
        "stats": {
            "total": stats_total,
            "liked": stats_liked,
            "disliked": stats_disliked,
            "favorited": stats_favorited,
            "transferred": stats_transferred,
            "no_feedback": max(0, stats_total - stats_liked - stats_disliked),
        },
    }


@router.get("/query-logs")
async def get_query_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询日志（操作日志，保留旧接口兼容）"""
    query = select(OperationLog).order_by(OperationLog.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    logs = result.scalars().all()

    return {
        "items": [
            {"id": l.id, "user_id": l.user_id, "action": l.action,
             "resource_type": l.resource_type, "resource_id": l.resource_id,
             "detail": l.detail, "ip_address": l.ip_address,
             "created_at": l.created_at.isoformat()}
            for l in logs
        ],
        "total": total,
    }


@router.get("/question-logs/{message_id}/detail")
async def get_question_log_detail(
    message_id: str,
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """提问日志详情 - 展示完整的 AI 问答分析过程"""
    from app.models import Favorite
    from app.adapters.ragflow_client import ragflow_client

    # 1. 查询用户消息
    msg_result = await db.execute(
        select(Message, User.display_name)
        .join(User, User.id == Message.user_id)
        .where(Message.id == message_id, Message.role == "user")
    )
    row = msg_result.first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="消息不存在")

    user_msg, user_name = row

    # 2. 查询同 session 的 AI 回答
    ai_result = await db.execute(
        select(Message)
        .where(
            Message.session_id == user_msg.session_id,
            Message.role == "assistant",
            Message.created_at >= user_msg.created_at,
        )
        .order_by(Message.created_at.asc())
        .limit(1)
    )
    ai_msg = ai_result.scalar_one_or_none()

    # 3. 查询 Session 信息
    session_result = await db.execute(
        select(Session).where(Session.id == user_msg.session_id)
    )
    session = session_result.scalar_one_or_none()

    # 4. 获取 RAGFlow 助手配置（模型信息）
    ragflow_info = {}
    if session and session.ragflow_conversation_id:
        try:
            chat_id = session.ragflow_conversation_id.split(":")[0]
            assistant = await ragflow_client.get_chat_assistant(chat_id)
            if assistant:
                llm_config = assistant.get("llm", {}) or {}
                ragflow_info = {
                    "assistant_name": assistant.get("name", "未知助手"),
                    "model_name": llm_config.get("model_name", "默认模型"),
                    "temperature": llm_config.get("temperature"),
                    "top_p": llm_config.get("top_p"),
                    "presence_penalty": llm_config.get("presence_penalty"),
                    "frequency_penalty": llm_config.get("frequency_penalty"),
                    "dataset_ids": assistant.get("dataset_ids", []),
                }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"获取RAGFlow助手信息失败: {e}")
            ragflow_info = {"error": str(e)}

    # 5. 解析引用信息 (citations) 和 RAGFlow 请求/响应
    citations = []
    ragflow_request = None
    ragflow_response = None
    if ai_msg and ai_msg.citations:
        raw_citations = ai_msg.citations
        if isinstance(raw_citations, dict):
            # 新格式: 含 ragflow_request / ragflow_response
            ragflow_request = raw_citations.get("ragflow_request")
            ragflow_response = raw_citations.get("ragflow_response")

            # 引用片段从 ragflow_response.reference 中取
            ref = (ragflow_response or {}).get("reference") or raw_citations
            chunks = ref.get("chunks", []) if isinstance(ref, dict) else []
            for chunk in chunks:
                citations.append({
                    "content": chunk.get("content", chunk.get("content_with_weight", "")),
                    "document_name": chunk.get("document_name", chunk.get("doc_name", "未知文档")),
                    "dataset_name": chunk.get("dataset_name", ""),
                    "similarity": chunk.get("similarity", chunk.get("score", 0)),
                    "vector_similarity": chunk.get("vector_similarity", 0),
                    "term_similarity": chunk.get("term_similarity", 0),
                })

    # 6. 查询反馈（T-17.1: 使用 message_id 匹配）
    # 先查对应 AI 消息的反馈，再查用户消息的反馈
    target_msg_id = ai_msg.id if ai_msg else message_id
    fb_result = await db.execute(
        select(Feedback).where(
            Feedback.message_id == target_msg_id,
            Feedback.user_id == user_msg.user_id,
        )
    )
    feedback_row = fb_result.scalar_one_or_none()
    feedback = None
    if feedback_row:
        feedback = {
            "type": feedback_row.type.value if feedback_row.type else None,
            "reason": feedback_row.reason,
            "created_at": feedback_row.created_at.isoformat() if feedback_row.created_at else None,
        }

    # 7. 收藏状态
    fav_result = await db.execute(
        select(func.count(Favorite.id)).where(Favorite.message_id == message_id)
    )
    is_favorited = (fav_result.scalar() or 0) > 0

    # 8. 转人工状态
    ticket_result = await db.execute(
        select(Ticket).where(
            Ticket.session_id == user_msg.session_id,
            Ticket.source == "manual",
        )
    )
    ticket_row = ticket_result.scalar_one_or_none()
    transfer_info = None
    if ticket_row:
        transfer_info = {
            "ticket_id": ticket_row.id,
            "status": ticket_row.status.value if ticket_row.status else None,
            "created_at": ticket_row.created_at.isoformat() if ticket_row.created_at else None,
        }

    # 9. 提取 timing 数据
    timing = None
    if ai_msg and ai_msg.citations and isinstance(ai_msg.citations, dict):
        timing = ai_msg.citations.get("timing")

    return {
        "user_question": user_msg.content,
        "ai_answer": ai_msg.content if ai_msg else "",
        "created_at": user_msg.created_at.isoformat(),
        "session_id": user_msg.session_id,
        "session_title": session.title if session else "未知会话",
        "user_name": user_name,
        "ragflow_info": ragflow_info,
        "ragflow_request": ragflow_request,
        "ragflow_response": ragflow_response,
        "citations": citations,
        "feedback": feedback,
        "is_favorited": is_favorited,
        "transfer_info": transfer_info,
        "timing": timing,
    }

