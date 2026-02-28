"""
连续踩检测规则 (T-024)
同session连续3次dislike → 建议转人工
"""
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Feedback, FeedbackType


async def check_consecutive_dislikes(
    session_id: str,
    db: AsyncSession,
    threshold: int = 3,
) -> bool:
    """检查同session是否连续踩达到阈值"""
    result = await db.execute(
        select(func.count(Feedback.id)).where(
            and_(
                Feedback.session_id == session_id,
                Feedback.type == FeedbackType.DISLIKE,
            )
        )
    )
    count = result.scalar() or 0
    return count >= threshold
