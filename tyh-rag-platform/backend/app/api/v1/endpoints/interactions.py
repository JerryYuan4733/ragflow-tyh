"""
反馈+工单+收藏+通知 接口
T-023: 反馈(2 API) + T-024: 连续踩检测
T-026: 工单(6 API)
T-027: 收藏(3 API)
T-028: 通知(2 API)
"""

import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_current_user, require_kb_admin
from app.db.session import get_db
from sqlalchemy.orm import joinedload

from app.models import (
    User, Feedback, FeedbackType, Ticket, TicketStatus,
    TicketLog, Favorite, Notification, Message, QAMeta, QAStatus,
)
from app.services.transfer_service import TransferService


# ==================== Feedback Router ====================
feedback_router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: str
    session_id: str
    type: str  # like / dislike
    reason_category: Optional[str] = None
    reason_custom: Optional[str] = None


@feedback_router.post("")
async def submit_feedback(
    request: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    反馈 Toggle 模式：
    - 无记录 → INSERT
    - 类型相同 → DELETE（取消反馈）
    - 类型不同 → UPDATE（切换反馈）
    """
    new_type = FeedbackType(request.type)

    # 查询已有反馈（唯一约束: user_id + message_id）
    existing = (await db.execute(
        select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.message_id == request.message_id,
        )
    )).scalar_one_or_none()

    result = {"id": None, "type": None, "suggest_transfer": False}

    if existing is None:
        # 无记录 → 创建
        fb = Feedback(
            id=str(uuid.uuid4()),
            message_id=request.message_id,
            session_id=request.session_id,
            user_id=user.id,
            type=new_type,
            reason_category=request.reason_category,
            reason_custom=request.reason_custom,
        )
        db.add(fb)
        await db.flush()
        result["id"] = fb.id
        result["type"] = new_type.value
    elif existing.type == new_type:
        # 类型相同 → 取消
        await db.delete(existing)
        await db.flush()
        # result 保持 id=None, type=None
    else:
        # 类型不同 → 切换
        existing.type = new_type
        existing.reason_category = request.reason_category
        existing.reason_custom = request.reason_custom
        await db.flush()
        result["id"] = existing.id
        result["type"] = new_type.value

    # 连续 3 踩检测（仅当当前操作结果为 dislike 时检查）
    if result["type"] == FeedbackType.DISLIKE.value:
        dislike_count = (await db.execute(
            select(func.count()).select_from(
                select(Feedback).where(
                    Feedback.session_id == request.session_id,
                    Feedback.user_id == user.id,
                    Feedback.type == FeedbackType.DISLIKE,
                ).subquery()
            )
        )).scalar() or 0
        if dislike_count >= 3:
            result["suggest_transfer"] = True

    return result


class TransferRequest(BaseModel):
    message_id: str


@feedback_router.post("/transfer")
async def transfer_to_human(
    request: TransferRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    转人工服务（重构）：
    自动创建待审核 QA + 工单，含幂等检查和 QA 重复检测
    """
    try:
        result = await TransferService.transfer(db, request.message_id, user)
        return {
            "qa_id": result.qa_id,
            "ticket_id": result.ticket_id,
            "message": result.message,
        }
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "ALREADY_TRANSFERRED":
            raise HTTPException(
                status_code=409,
                detail="该消息已转人工"
            )
        elif error_msg.startswith("DUPLICATE_QA"):
            parts = error_msg.split("|")
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "转人工失败：该问题已存在 QA 记录",
                    "duplicate_qa_id": parts[1] if len(parts) > 1 else None,
                    "duplicate_question": parts[2] if len(parts) > 2 else None,
                    "similarity": float(parts[3]) if len(parts) > 3 else None,
                }
            )
        elif error_msg == "MESSAGE_NOT_FOUND":
            raise HTTPException(status_code=404, detail="消息不存在")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Ticket Router ====================
ticket_router = APIRouter()


@ticket_router.get("")
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取工单列表"""
    from sqlalchemy.orm import aliased
    Assignee = aliased(User, name="assignee")

    query = (
        select(Ticket, Assignee.display_name.label("assignee_name"))
        .outerjoin(Assignee, Ticket.assignee_id == Assignee.id)
    )
    if status:
        query = query.where(Ticket.status == TicketStatus(status))

    count_query = select(Ticket)
    if status:
        count_query = count_query.where(Ticket.status == TicketStatus(status))
    total = (await db.execute(select(func.count()).select_from(count_query.subquery()))).scalar() or 0

    result = await db.execute(query.order_by(Ticket.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    rows = result.all()

    return {
        "items": [
            {"id": t.id, "title": t.title, "status": t.status.value,
             "source": t.source, "assigned_to_name": assignee_name,
             "created_at": t.created_at.isoformat()}
            for t, assignee_name in rows
        ],
        "total": total,
    }


@ticket_router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取工单详情（含关联 QA）"""
    # T-14.1: eager load QA 关系
    result = await db.execute(
        select(Ticket).options(joinedload(Ticket.qa)).where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    # T-14.2: 响应新增 qa 字段
    resp = {
        "id": ticket.id, "title": ticket.title, "description": ticket.description,
        "status": ticket.status.value, "source": ticket.source,
        "created_at": ticket.created_at.isoformat(),
        "qa": None,
    }
    if ticket.qa:
        resp["qa"] = {
            "id": ticket.qa.id,
            "question": ticket.qa.question,
            "answer": ticket.qa.answer,
            "status": ticket.qa.status.value if hasattr(ticket.qa.status, 'value') else str(ticket.qa.status),
            "version": ticket.qa.version,
        }
    return resp


async def _update_ticket_status(
    db: AsyncSession, ticket_id: str, user: User,
    new_status: TicketStatus, action: str
):
    """工单状态流转通用方法"""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    ticket.status = new_status
    if new_status == TicketStatus.PROCESSING:
        ticket.assignee_id = user.id
    elif new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)
    elif new_status == TicketStatus.VERIFIED:
        ticket.verified_at = datetime.now(timezone.utc)

    # 操作日志
    log = TicketLog(
        id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        operator_id=user.id,
        action=action,
    )
    db.add(log)

    # 通知
    notif = Notification(
        id=str(uuid.uuid4()),
        user_id=ticket.creator_id,
        ticket_id=ticket_id,
        type="ticket_update",
        title=f"工单状态更新: {action}",
    )
    db.add(notif)
    await db.flush()
    return {"message": f"工单已{action}", "status": new_status.value}


@ticket_router.put("/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, user: User = Depends(require_kb_admin), db: AsyncSession = Depends(get_db)):
    """认领工单"""
    return await _update_ticket_status(db, ticket_id, user, TicketStatus.PROCESSING, "认领")


class ResolveRequest(BaseModel):
    qa_question: Optional[str] = None
    qa_answer: Optional[str] = None
    approve_qa: Optional[bool] = None  # 标记 QA 为已审核（状态→active）


@ticket_router.put("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    request: ResolveRequest = ResolveRequest(),
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """解决工单（可同时编辑关联 QA）"""
    # T-14.3~14.5: 解决工单时更新关联 QA
    result = await db.execute(
        select(Ticket).options(joinedload(Ticket.qa)).where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # 更新关联 QA
    qa_updated = False
    if ticket.qa:
        content_changed = False
        if request.qa_question is not None:
            ticket.qa.question = request.qa_question
            ticket.qa.question_summary = request.qa_question[:200]
            content_changed = True
        if request.qa_answer is not None:
            ticket.qa.answer = request.qa_answer
            ticket.qa.answer_summary = request.qa_answer[:200]
            content_changed = True
        if content_changed:
            ticket.qa.version += 1
        # 编辑内容 或 勾选审核通过 → 状态改为 active
        if content_changed or request.approve_qa:
            ticket.qa.status = QAStatus.ACTIVE
            ticket.qa.edited_by = user.id
            qa_updated = True

    # 状态流转
    status_result = await _update_ticket_status(db, ticket_id, user, TicketStatus.RESOLVED, "解决")

    # T-14.5: QA 更新后不再自动同步到 RAGFlow（V2 改为手动推送）

    return status_result


@ticket_router.put("/{ticket_id}/verify")
async def verify_ticket(ticket_id: str, user: User = Depends(require_kb_admin), db: AsyncSession = Depends(get_db)):
    """验证工单"""
    return await _update_ticket_status(db, ticket_id, user, TicketStatus.VERIFIED, "验证")


@ticket_router.put("/{ticket_id}/reopen")
async def reopen_ticket(ticket_id: str, user: User = Depends(require_kb_admin), db: AsyncSession = Depends(get_db)):
    """重开工单（FR-35: 关联 QA 状态回退为 pending_review）"""
    # FR-35: 加载关联 QA，重开时将 QA 状态回退
    result = await db.execute(
        select(Ticket).options(joinedload(Ticket.qa)).where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # FR-35: 关联 QA 状态回退为待审核
    if ticket.qa and ticket.qa.status != QAStatus.PENDING_REVIEW:
        ticket.qa.status = QAStatus.PENDING_REVIEW

    return await _update_ticket_status(db, ticket_id, user, TicketStatus.PENDING, "重开")


# ==================== Favorite Router ====================
favorite_router = APIRouter()


class FavoriteToggleRequest(BaseModel):
    message_id: str


@favorite_router.post("/toggle")
async def toggle_favorite(
    request: FavoriteToggleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """收藏 Toggle：存在则取消，不存在则添加"""
    existing = (await db.execute(
        select(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.message_id == request.message_id,
        )
    )).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.flush()
        return {"is_favorited": False, "id": None}
    else:
        fav = Favorite(id=str(uuid.uuid4()), user_id=user.id, message_id=request.message_id)
        db.add(fav)
        await db.flush()
        return {"is_favorited": True, "id": fav.id}


@favorite_router.post("")
async def add_favorite(
    message_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """收藏消息（兼容旧接口，推荐使用 /toggle）"""
    fav = Favorite(id=str(uuid.uuid4()), user_id=user.id, message_id=message_id)
    db.add(fav)
    await db.flush()
    return {"id": fav.id}


@favorite_router.get("")
async def list_favorites(
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """收藏列表（含消息内容预览）"""
    from app.models import Session as ChatSession
    result = await db.execute(
        select(Favorite, Message.content, Message.role, Message.session_id, Message.created_at.label("msg_created_at"))
        .join(Message, Favorite.message_id == Message.id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc()).limit(50)
    )
    rows = result.all()
    return {"items": [
        {
            "id": f.id,
            "message_id": f.message_id,
            "content": content[:200] if content else "",
            "role": role.value if hasattr(role, 'value') else str(role),
            "session_id": session_id,
            "created_at": f.created_at.isoformat(),
            "msg_created_at": msg_created_at.isoformat() if msg_created_at else None,
        }
        for f, content, role, session_id, msg_created_at in rows
    ]}


@favorite_router.delete("/{fav_id}")
async def remove_favorite(
    fav_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消收藏"""
    result = await db.execute(select(Favorite).where(Favorite.id == fav_id, Favorite.user_id == user.id))
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="收藏不存在")
    await db.delete(fav)
    await db.flush()
    return {"message": "取消成功"}


# ==================== Notification Router ====================
notification_router = APIRouter()


@notification_router.get("")
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取未读通知列表"""
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.is_read == False)
        .order_by(Notification.created_at.desc()).limit(50)
    )
    items = result.scalars().all()
    return {
        "items": [
            {"id": n.id, "type": n.type, "title": n.title, "content": n.content,
             "ticket_id": n.ticket_id, "created_at": n.created_at.isoformat()}
            for n in items
        ],
        "unread_count": len(items),
    }


@notification_router.put("/read")
async def mark_read(
    notification_ids: list[str],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记通知已读"""
    result = await db.execute(
        select(Notification).where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user.id,
        )
    )
    for notif in result.scalars().all():
        notif.is_read = True
    await db.flush()
    return {"message": "已标记已读"}
