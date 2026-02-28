"""
转人工服务
编排转人工完整流程: 幂等检查 → 获取问答 → 重复检测 → 创建 QA + Ticket
"""

import uuid
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User, Message, MessageRole, QAMeta, QAStatus, QASource,
    Ticket, TicketStatus, Session,
)
from app.services.qa_duplicate_detector import QADuplicateDetector

logger = logging.getLogger(__name__)


@dataclass
class TransferResult:
    """转人工结果"""
    qa_id: str
    ticket_id: str
    message: str


class TransferService:
    """转人工服务 — 业务编排层"""

    @staticmethod
    async def transfer(
        db: AsyncSession,
        message_id: str,
        user: User,
    ) -> TransferResult:
        """
        转人工核心流程:
        1. 幂等检查（该消息是否已转人工）
        2. 获取 AI 消息 + 对应 user 提问
        3. QA 重复检测
        4. 创建 QA (pending_review, source=transfer)
        5. 创建 Ticket (关联 QA)

        Raises:
            ValueError: 幂等冲突(已转人工) 或 QA 重复
        """
        # 1. 幂等检查：该消息是否已转人工
        existing_qa = (await db.execute(
            select(QAMeta).where(
                QAMeta.source_message_id == message_id,
                QAMeta.source == QASource.TRANSFER,
            )
        )).scalar_one_or_none()

        if existing_qa:
            raise ValueError("ALREADY_TRANSFERRED")

        # 2. 获取 AI 消息（message_id 指向的应该是 AI 消息）
        ai_msg = (await db.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()

        if not ai_msg:
            raise ValueError("MESSAGE_NOT_FOUND")

        # 获取该 AI 消息对应的用户提问（同 session，role=user，时间在 AI 消息之前的最近一条）
        user_msg = (await db.execute(
            select(Message).where(
                Message.session_id == ai_msg.session_id,
                Message.role == MessageRole.USER,
                Message.created_at <= ai_msg.created_at,
            ).order_by(Message.created_at.desc()).limit(1)
        )).scalar_one_or_none()

        question = user_msg.content[:500] if user_msg else "用户主动转人工"
        answer = ai_msg.content[:2000] if ai_msg.role == MessageRole.ASSISTANT else ""

        # 3. QA 重复检测
        team_id = user.active_team_id
        duplicate = await QADuplicateDetector.check(db, question, team_id)
        if duplicate:
            raise ValueError(
                f"DUPLICATE_QA|{duplicate.qa_id}|{duplicate.question[:100]}|{duplicate.similarity}"
            )

        # 4. 创建 QA（状态: 待审核，来源: 转人工）
        qa = QAMeta(
            id=str(uuid.uuid4()),
            team_id=team_id,
            question=question,
            answer=answer,
            status=QAStatus.PENDING_REVIEW,
            source=QASource.TRANSFER,
            source_message_id=message_id,
            edited_by=user.id,
        )
        db.add(qa)
        await db.flush()

        # 5. 创建工单（关联 QA）
        ticket = Ticket(
            id=str(uuid.uuid4()),
            qa_id=qa.id,
            session_id=ai_msg.session_id,
            creator_id=user.id,
            title=question[:200],
            source="manual",
            source_message_id=message_id,
            status=TicketStatus.PENDING,
        )
        db.add(ticket)
        await db.flush()

        logger.info(f"转人工成功: qa_id={qa.id}, ticket_id={ticket.id}, message_id={message_id}")

        return TransferResult(
            qa_id=qa.id,
            ticket_id=ticket.id,
            message="已转接人工服务",
        )
