"""
公告接口 - 5 API (T-046 + FR-38)
active, list, create, update, delete
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_current_user, require_it_admin
from app.db.session import get_db
from app.models import User, Announcement

router = APIRouter()


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    scheduled_at: Optional[str] = None  # FR-38: ISO 8601 格式定时发布时间


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    scheduled_at: Optional[str] = None  # FR-38: 传 null 清除定时


@router.get("/active")
async def get_active_announcements(
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前生效公告（FR-38: 增加 scheduled_at 判断）"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Announcement)
        .where(
            Announcement.is_active == True,
            or_(Announcement.scheduled_at.is_(None), Announcement.scheduled_at <= now),
        )
        .order_by(Announcement.created_at.desc())
        .limit(5)
    )
    items = result.scalars().all()
    return {
        "items": [
            {"id": a.id, "title": a.title, "content": a.content,
             "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
             "created_at": a.created_at.isoformat()}
            for a in items
        ]
    }


@router.get("")
async def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _=Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取公告列表(管理) - FR-38: 权限收紧为 IT 管理员"""
    query = select(Announcement).order_by(Announcement.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()

    return {
        "items": [
            {"id": a.id, "title": a.title, "content": a.content,
             "is_active": a.is_active,
             "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
             "created_at": a.created_at.isoformat()}
            for a in items
        ],
        "total": total,
    }


@router.post("", status_code=201)
async def create_announcement(
    request: AnnouncementCreate,
    user: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建公告 - FR-38: 权限收紧 + 支持 scheduled_at"""
    ann = Announcement(
        id=str(uuid.uuid4()),
        title=request.title,
        content=request.content,
        scheduled_at=datetime.fromisoformat(request.scheduled_at) if request.scheduled_at else None,
        created_by=user.id,
    )
    db.add(ann)
    await db.flush()
    return {"id": ann.id, "message": "创建成功"}


@router.put("/{ann_id}")
async def update_announcement(
    ann_id: str,
    request: AnnouncementUpdate,
    _=Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新公告 - FR-38: 权限收紧 + 支持 scheduled_at"""
    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    if request.title is not None:
        ann.title = request.title
    if request.content is not None:
        ann.content = request.content
    if request.is_active is not None:
        ann.is_active = request.is_active
    # FR-38: scheduled_at 支持传 null 清除定时
    if "scheduled_at" in (request.model_fields_set or set()):
        ann.scheduled_at = datetime.fromisoformat(request.scheduled_at) if request.scheduled_at else None
    await db.flush()
    return {"message": "更新成功"}


@router.delete("/{ann_id}")
async def delete_announcement(
    ann_id: str,
    _=Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除公告 - FR-38: 新增"""
    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    await db.delete(ann)
    await db.flush()
    return {"message": "公告已删除"}
