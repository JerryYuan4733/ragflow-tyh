"""团队管理服务 - 核心业务逻辑"""

import uuid
import logging
from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Team, User, UserTeam, TeamConfig, TeamDataset, UserRole
from app.adapters.ragflow_client import ragflow_client

logger = logging.getLogger(__name__)


class TeamService:
    """团队服务 - 团队CRUD、成员管理、配置管理"""

    # ==================== 团队 CRUD ====================

    @staticmethod
    async def list_teams(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        """获取团队列表（含统计信息）"""
        query = select(Team)
        if keyword:
            query = query.where(Team.name.contains(keyword))

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # 分页
        query = query.order_by(Team.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        teams = list(result.scalars().all())

        # 补充统计信息
        items = []
        for team in teams:
            # 成员数
            member_count = (await db.execute(
                select(func.count()).where(UserTeam.team_id == team.id)
            )).scalar() or 0

            # 是否已绑定助手
            config_result = await db.execute(
                select(TeamConfig).where(TeamConfig.team_id == team.id)
            )
            config = config_result.scalar_one_or_none()
            has_assistant = bool(config and config.ragflow_assistant_id)

            # 知识库数
            dataset_count = (await db.execute(
                select(func.count()).where(TeamDataset.team_id == team.id)
            )).scalar() or 0

            items.append({
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "member_count": member_count,
                "has_assistant": has_assistant,
                "dataset_count": dataset_count,
                "created_at": team.created_at.isoformat() if team.created_at else "",
                "updated_at": team.updated_at.isoformat() if team.updated_at else "",
            })

        return items, total

    @staticmethod
    async def get_team(db: AsyncSession, team_id: str) -> Optional[Team]:
        """获取团队详情"""
        result = await db.execute(select(Team).where(Team.id == team_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_team(
        db: AsyncSession,
        name: str,
        description: Optional[str] = None,
    ) -> Team:
        """创建团队，同时创建空的 TeamConfig"""
        # 检查名称唯一
        existing = await db.execute(select(Team).where(Team.name == name))
        if existing.scalar_one_or_none():
            raise ValueError(f"团队名称 '{name}' 已存在")

        team_id = str(uuid.uuid4())
        team = Team(id=team_id, name=name, description=description)
        db.add(team)

        # 创建空配置
        config = TeamConfig(
            id=str(uuid.uuid4()),
            team_id=team_id,
        )
        db.add(config)

        # 自动将所有IT管理员加入新团队
        it_admins_result = await db.execute(
            select(User).where(User.role == UserRole.IT_ADMIN)
        )
        it_admins = list(it_admins_result.scalars().all())
        for admin in it_admins:
            ut = UserTeam(
                id=str(uuid.uuid4()),
                user_id=admin.id,
                team_id=team_id,
                is_default=False,
            )
            db.add(ut)
            # 如果IT管理员没有活跃团队，自动设置
            if not admin.active_team_id:
                admin.active_team_id = team_id
        logger.info(f"团队 '{name}' 创建成功，已自动添加 {len(it_admins)} 个IT管理员")

        await db.flush()
        return team

    @staticmethod
    async def update_team(
        db: AsyncSession,
        team_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Team:
        """编辑团队基本信息"""
        result = await db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team:
            raise ValueError("团队不存在")

        if name is not None:
            # 检查名称唯一（排除自身）
            existing = await db.execute(
                select(Team).where(Team.name == name, Team.id != team_id)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"团队名称 '{name}' 已存在")
            team.name = name
        if description is not None:
            team.description = description

        await db.flush()
        return team

    @staticmethod
    async def delete_team(db: AsyncSession, team_id: str) -> None:
        """删除团队（cascade 会自动清理子记录）"""
        result = await db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team:
            raise ValueError("团队不存在")

        # 检查是否有用户以此为活跃团队
        active_count = (await db.execute(
            select(func.count()).where(User.active_team_id == team_id)
        )).scalar() or 0
        if active_count > 0:
            raise ValueError(f"团队中仍有 {active_count} 个用户以此为活跃团队，请先切换他们的活跃团队")

        await db.delete(team)
        await db.flush()

    # ==================== 成员管理 ====================

    @staticmethod
    async def list_members(db: AsyncSession, team_id: str) -> list[dict]:
        """获取团队成员列表"""
        result = await db.execute(
            select(UserTeam, User)
            .join(User, UserTeam.user_id == User.id)
            .where(UserTeam.team_id == team_id)
            .order_by(UserTeam.created_at.asc())
        )
        rows = result.all()

        members = []
        for ut, user in rows:
            members.append({
                "user_id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role.value,
                "is_default": ut.is_default,
                "joined_at": ut.created_at.isoformat() if ut.created_at else "",
            })
        return members

    @staticmethod
    async def add_members(
        db: AsyncSession,
        team_id: str,
        user_ids: list[str],
        set_default: bool = False,
    ) -> int:
        """批量添加团队成员，返回成功添加数"""
        # 验证团队存在
        team = await TeamService.get_team(db, team_id)
        if not team:
            raise ValueError("团队不存在")

        added = 0
        for uid in user_ids:
            # 检查用户是否存在
            user_result = await db.execute(select(User).where(User.id == uid))
            if not user_result.scalar_one_or_none():
                logger.warning(f"用户 {uid} 不存在，跳过")
                continue

            # 检查是否已关联
            existing = await db.execute(
                select(UserTeam).where(
                    UserTeam.user_id == uid, UserTeam.team_id == team_id
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"用户 {uid} 已在团队 {team_id} 中，跳过")
                continue

            ut = UserTeam(
                id=str(uuid.uuid4()),
                user_id=uid,
                team_id=team_id,
                is_default=set_default,
            )
            db.add(ut)
            added += 1

            # 如果用户没有活跃团队，自动设置
            user_result2 = await db.execute(select(User).where(User.id == uid))
            user = user_result2.scalar_one_or_none()
            if user and not user.active_team_id:
                user.active_team_id = team_id

        await db.flush()
        return added

    @staticmethod
    async def remove_member(db: AsyncSession, team_id: str, user_id: str) -> None:
        """移除团队成员（IT管理员不可被移除）"""
        # 检查目标用户是否为IT管理员
        user_check = await db.execute(select(User).where(User.id == user_id))
        target_user = user_check.scalar_one_or_none()
        if target_user and target_user.role == UserRole.IT_ADMIN:
            raise ValueError("IT管理员默认属于所有团队，无法移除")

        result = await db.execute(
            select(UserTeam).where(
                UserTeam.user_id == user_id, UserTeam.team_id == team_id
            )
        )
        ut = result.scalar_one_or_none()
        if not ut:
            raise ValueError("该用户不在此团队中")

        await db.delete(ut)

        # 如果该团队是用户的活跃团队，切换到其他团队
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.active_team_id == team_id:
            # 查找用户其他团队
            other_result = await db.execute(
                select(UserTeam).where(
                    UserTeam.user_id == user_id, UserTeam.team_id != team_id
                ).limit(1)
            )
            other_ut = other_result.scalar_one_or_none()
            user.active_team_id = other_ut.team_id if other_ut else None

        await db.flush()

    # ==================== 助手配置 ====================

    @staticmethod
    async def get_config(db: AsyncSession, team_id: str) -> Optional[TeamConfig]:
        """获取团队配置"""
        result = await db.execute(
            select(TeamConfig).where(TeamConfig.team_id == team_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def bind_assistant(
        db: AsyncSession,
        team_id: str,
        ragflow_assistant_id: str,
    ) -> TeamConfig:
        """绑定 RAGFlow 助手"""
        # 验证团队存在
        team = await TeamService.get_team(db, team_id)
        if not team:
            raise ValueError("团队不存在")

        # 从 RAGFlow 获取助手名称（可选，失败不阻塞）
        assistant_name = None
        try:
            assistant = await ragflow_client.get_chat_assistant(ragflow_assistant_id)
            if assistant:
                assistant_name = assistant.get("name")
        except Exception as e:
            logger.warning(f"从 RAGFlow 获取助手信息失败: {e}")

        # 更新或创建配置
        result = await db.execute(
            select(TeamConfig).where(TeamConfig.team_id == team_id)
        )
        config = result.scalar_one_or_none()
        if config:
            config.ragflow_assistant_id = ragflow_assistant_id
            config.ragflow_assistant_name = assistant_name
        else:
            config = TeamConfig(
                id=str(uuid.uuid4()),
                team_id=team_id,
                ragflow_assistant_id=ragflow_assistant_id,
                ragflow_assistant_name=assistant_name,
            )
            db.add(config)

        await db.flush()
        return config

    # ==================== 知识库绑定 ====================

    @staticmethod
    async def list_datasets(db: AsyncSession, team_id: str) -> list[TeamDataset]:
        """获取团队绑定的知识库列表"""
        result = await db.execute(
            select(TeamDataset).where(TeamDataset.team_id == team_id)
            .order_by(TeamDataset.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def set_datasets(
        db: AsyncSession,
        team_id: str,
        dataset_ids: list[str],
    ) -> list[TeamDataset]:
        """全量替换团队知识库绑定"""
        # 验证团队存在
        team = await TeamService.get_team(db, team_id)
        if not team:
            raise ValueError("团队不存在")

        # 删除旧绑定
        await db.execute(
            delete(TeamDataset).where(TeamDataset.team_id == team_id)
        )

        # 创建新绑定
        new_datasets = []
        for ds_id in dataset_ids:
            # 从 RAGFlow 获取知识库信息（可选）
            ds_name = None
            doc_count = 0
            chunk_count = 0
            try:
                datasets = await ragflow_client.list_datasets()
                for ds in datasets:
                    if ds.id == ds_id:
                        ds_name = ds.name
                        doc_count = ds.document_count or ds.doc_num or 0
                        chunk_count = ds.chunk_count or ds.chunk_num or 0
                        break
            except Exception as e:
                logger.warning(f"从 RAGFlow 获取知识库信息失败: {e}")

            td = TeamDataset(
                id=str(uuid.uuid4()),
                team_id=team_id,
                ragflow_dataset_id=ds_id,
                ragflow_dataset_name=ds_name,
                document_count=doc_count,
                chunk_count=chunk_count,
            )
            db.add(td)
            new_datasets.append(td)

        await db.flush()
        return new_datasets

    # ==================== 高频查询（对话/文档使用） ====================

    @staticmethod
    async def get_team_assistant_id(db: AsyncSession, team_id: str) -> Optional[str]:
        """获取团队绑定的助手ID（对话时使用，高频调用）"""
        result = await db.execute(
            select(TeamConfig.ragflow_assistant_id).where(TeamConfig.team_id == team_id)
        )
        row = result.first()
        return row[0] if row else None

    @staticmethod
    async def get_team_dataset_ids(db: AsyncSession, team_id: str) -> list[str]:
        """获取团队绑定的知识库ID列表（文档管理使用）"""
        result = await db.execute(
            select(TeamDataset.ragflow_dataset_id).where(TeamDataset.team_id == team_id)
        )
        return [row[0] for row in result.all()]
