"""
过期检测+质量评分 (T-049/T-050)
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentMeta, Notification
import uuid

logger = logging.getLogger(__name__)


async def check_expired_documents(db: AsyncSession):
    """
    定时任务: 每日检查过期文档
    - 已过期: 标记 is_expired = True
    - 7天内过期: 发送通知
    """
    now = datetime.now(timezone.utc)
    warn_date = now + timedelta(days=7)

    # 标记已过期
    result = await db.execute(
        select(DocumentMeta).where(
            DocumentMeta.expires_at <= now,
            DocumentMeta.is_expired == False,
        )
    )
    expired_docs = result.scalars().all()
    for doc in expired_docs:
        doc.is_expired = True
        logger.info(f"Document {doc.filename} marked as expired")

    # 即将过期通知
    result = await db.execute(
        select(DocumentMeta).where(
            DocumentMeta.expires_at.between(now, warn_date),
            DocumentMeta.is_expired == False,
        )
    )
    about_to_expire = result.scalars().all()
    for doc in about_to_expire:
        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=doc.uploaded_by,
            type="document_expiring",
            title=f"文档即将过期: {doc.filename}",
            content=f"该文档将于 {doc.expires_at.isoformat()} 过期，请及时更新。",
        )
        db.add(notif)
        logger.info(f"Expiry warning for {doc.filename}")

    await db.flush()
    return len(expired_docs), len(about_to_expire)


def calculate_quality_score(
    chunk_count: int,
    file_size: int,
    parse_progress: float = 1.0,
) -> float:
    """
    文档质量评分算法 (T-050)
    基于: chunk数量 × 解析完成度
    评分范围: 0-100
    """
    if chunk_count == 0:
        return 0.0

    # 基础分: chunk密度 (每MB产生的chunk数)
    size_mb = max(file_size / (1024 * 1024), 0.01)
    density = min(chunk_count / size_mb, 50)  # cap at 50 chunks/MB
    density_score = min(density / 50 * 60, 60)  # 最高60分

    # 解析完成度: 40分
    progress_score = parse_progress * 40

    return round(density_score + progress_score, 1)
