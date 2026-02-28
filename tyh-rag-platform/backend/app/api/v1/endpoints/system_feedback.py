"""
系统反馈接口 (T-047)
- POST: 提交系统体验反馈
- GET: 查看反馈列表（管理员）
"""
import uuid
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_kb_admin
from app.db.session import get_db
from app.models import User, OperationLog

router = APIRouter()


class SystemFeedbackRequest(BaseModel):
    category: str  # 功能建议/Bug反馈/体验评价
    content: str
    rating: int = 0  # 1-5


@router.get("")
async def list_system_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """查看意见反馈列表（管理员）"""
    base_query = select(OperationLog).where(OperationLog.action == "system_feedback")

    total = (await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )).scalar() or 0

    result = await db.execute(
        base_query.order_by(OperationLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()

    items = []
    for log in logs:
        # detail 格式: "[分类] rating=N: 内容"
        detail = log.detail or ""
        category = ""
        rating = 0
        content = detail
        if detail.startswith("["):
            bracket_end = detail.find("]")
            if bracket_end > 0:
                category = detail[1:bracket_end]
                rest = detail[bracket_end + 1:].strip()
                if rest.startswith("rating="):
                    colon_pos = rest.find(":")
                    if colon_pos > 0:
                        try:
                            rating = int(rest[7:colon_pos])
                        except ValueError:
                            pass
                        content = rest[colon_pos + 1:].strip()
                    else:
                        content = rest
                else:
                    content = rest

        items.append({
            "id": log.id,
            "user_id": log.user_id,
            "category": category,
            "rating": rating,
            "content": content,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {"items": items, "total": total}


@router.post("", status_code=201)
async def submit_system_feedback(
    request: SystemFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交系统体验反馈"""
    log = OperationLog(
        id=str(uuid.uuid4()),
        user_id=user.id,
        action="system_feedback",
        resource_type="system",
        resource_id=None,
        detail=f"[{request.category}] rating={request.rating}: {request.content}",
        ip_address=None,
    )
    db.add(log)
    await db.flush()
    return {"message": "感谢您的反馈！"}

