"""操作日志审计装饰器 (T-029)"""

import uuid
import functools
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.models import OperationLog, User

logger = logging.getLogger(__name__)


async def log_operation(
    db: AsyncSession,
    user: User,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """记录操作日志"""
    log = OperationLog(
        id=str(uuid.uuid4()),
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()
