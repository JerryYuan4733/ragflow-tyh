"""
对话接口 - 7 API
T-015: sessions CRUD + messages SSE + suggestions + search
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User, Message, Feedback, Favorite, QAMeta, QASource
from app.schemas.chat import (
    SessionCreateRequest, SessionResponse,
    MessageRequest, MessageResponse, SuggestionResponse,
)
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    request: SessionCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新对话会话"""
    session = await ChatService.create_session(db, user, request.title)
    return SessionResponse(
        id=session.id, title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.get("/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话列表"""
    sessions, total = await ChatService.list_sessions(db, user, page, page_size)
    return {
        "items": [
            SessionResponse(
                id=s.id, title=s.title,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            ) for s in sessions
        ],
        "total": total,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话"""
    try:
        await ChatService.delete_session(db, session_id, user)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: MessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息 - SSE流式返回AI回答（FR-39: 支持 thinking 参数）"""
    return StreamingResponse(
        ChatService.send_message_stream(db, session_id, user, request.content, thinking=request.thinking),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话历史消息（含反馈/收藏/转人工状态）"""
    # 单次查询：LEFT JOIN 获取所有交互状态，避免 N+1 问题
    query = (
        select(
            Message,
            Feedback.type.label("feedback_type"),
            func.count(Favorite.id).label("fav_count"),
            func.count(QAMeta.id).label("transfer_count"),
        )
        .outerjoin(Feedback, and_(
            Feedback.message_id == Message.id,
            Feedback.user_id == user.id,
        ))
        .outerjoin(Favorite, and_(
            Favorite.message_id == Message.id,
            Favorite.user_id == user.id,
        ))
        .outerjoin(QAMeta, and_(
            QAMeta.source_message_id == Message.id,
            QAMeta.source == QASource.TRANSFER,
        ))
        .where(
            Message.session_id == session_id,
            Message.user_id == user.id,
        )
        .group_by(Message.id, Feedback.type)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(query)
    rows = result.all()

    return {
        "items": [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": msg.content,
                "citations": msg.citations,
                "created_at": msg.created_at.isoformat(),
                "feedback_type": fb_type.value if fb_type else None,
                "is_favorited": fav_count > 0,
                "is_transferred": transfer_count > 0,
            }
            for msg, fb_type, fav_count, transfer_count in rows
        ]
    }


@router.get("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(user: User = Depends(get_current_user)):
    """获取推荐问题"""
    questions = await ChatService.get_suggestions()
    return SuggestionResponse(questions=questions)


@router.get("/search")
async def search_messages(
    keyword: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索历史消息"""
    messages = await ChatService.search_messages(db, user, keyword)
    return {
        "items": [
            {
                "id": m.id,
                "role": m.role.value,
                "content": m.content,
                "session_id": m.session_id,
                "created_at": m.created_at.isoformat(),
            } for m in messages
        ]
    }
