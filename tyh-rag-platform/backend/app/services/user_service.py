"""用户管理服务"""

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import get_password_hash
from app.models import User, UserTeam, UserRole


class UserService:
    """用户管理服务 - 应用层"""

    @staticmethod
    async def get_users(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        team_id: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> tuple[list[User], int]:
        """获取用户列表 (分页)"""
        query = select(User).options(joinedload(User.active_team))

        if team_id:
            # 按团队过滤：通过 user_teams 关联表查询
            query = query.where(
                User.id.in_(
                    select(UserTeam.user_id).where(UserTeam.team_id == team_id)
                )
            )
        if keyword:
            query = query.where(
                User.username.contains(keyword) | User.display_name.contains(keyword)
            )

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        users = list(result.scalars().unique().all())

        return users, total

    @staticmethod
    async def create_user(
        db: AsyncSession,
        username: str,
        password: str,
        display_name: str,
        role: str,
        team_ids: list[str],
        job_number: Optional[str] = None,
    ) -> User:
        """创建用户，并关联到指定团队"""
        # 检查用户名唯一
        existing = await db.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"用户名 '{username}' 已存在")

        # 默认活跃团队为第一个团队
        active_team_id = team_ids[0] if team_ids else None

        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username=username,
            password_hash=get_password_hash(password),
            display_name=display_name,
            role=UserRole(role),
            active_team_id=active_team_id,
            job_number=job_number,
        )
        db.add(user)

        # 创建用户-团队关联
        for i, tid in enumerate(team_ids):
            ut = UserTeam(
                id=str(uuid.uuid4()),
                user_id=user_id,
                team_id=tid,
                is_default=(i == 0),
            )
            db.add(ut)

        await db.flush()
        return user

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: str,
        **kwargs,
    ) -> User:
        """更新用户信息"""
        result = await db.execute(
            select(User).options(joinedload(User.active_team)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("用户不存在")

        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                if key == "role":
                    setattr(user, key, UserRole(value))
                else:
                    setattr(user, key, value)

        await db.flush()
        return user

    @staticmethod
    async def toggle_user(db: AsyncSession, user_id: str) -> User:
        """启用/禁用用户"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("用户不存在")

        user.is_active = not user.is_active
        await db.flush()
        return user
