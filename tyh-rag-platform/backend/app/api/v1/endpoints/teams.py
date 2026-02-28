"""团队管理接口 - CRUD + 成员管理 + 配置管理"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_it_admin
from app.db.session import get_db
from app.models import User
from app.schemas.team import (
    TeamCreate, TeamUpdate, TeamResponse, TeamListResponse,
    MemberAdd, MemberResponse, MemberListResponse,
    ConfigUpdate, ConfigResponse,
    DatasetBind, DatasetItem, DatasetListResponse,
)
from app.services.team_service import TeamService

router = APIRouter()


# ==================== 团队 CRUD ====================

@router.get("", response_model=TeamListResponse)
async def list_teams(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取团队列表（所有已认证用户可访问）"""
    items, total = await TeamService.list_teams(db, page, page_size, keyword)
    return TeamListResponse(
        items=[TeamResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个团队详情"""
    # 复用 list_teams 的统计逻辑获取完整信息
    items, _ = await TeamService.list_teams(db, page=1, page_size=1, keyword=None)
    # 直接查询单个团队
    team = await TeamService.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 获取统计信息
    from sqlalchemy import select, func
    from app.models import UserTeam, TeamConfig, TeamDataset
    member_count = (await db.execute(
        select(func.count()).where(UserTeam.team_id == team_id)
    )).scalar() or 0
    config_result = await db.execute(select(TeamConfig).where(TeamConfig.team_id == team_id))
    config = config_result.scalar_one_or_none()
    dataset_count = (await db.execute(
        select(func.count()).where(TeamDataset.team_id == team_id)
    )).scalar() or 0

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        member_count=member_count,
        has_assistant=bool(config and config.ragflow_assistant_id),
        dataset_count=dataset_count,
        created_at=team.created_at.isoformat() if team.created_at else "",
        updated_at=team.updated_at.isoformat() if team.updated_at else "",
    )


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    request: TeamCreate,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建团队（仅IT管理员，自动添加所有IT管理员为成员）"""
    try:
        team = await TeamService.create_team(db, name=request.name, description=request.description)
        # 统计自动添加的IT管理员数量
        from sqlalchemy import select, func
        from app.models import UserTeam
        member_count = (await db.execute(
            select(func.count()).where(UserTeam.team_id == team.id)
        )).scalar() or 0
        return TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            member_count=member_count,
            has_assistant=False,
            dataset_count=0,
            created_at=team.created_at.isoformat() if team.created_at else "",
            updated_at=team.updated_at.isoformat() if team.updated_at else "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    request: TeamUpdate,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑团队（仅IT管理员）"""
    try:
        team = await TeamService.update_team(
            db, team_id, name=request.name, description=request.description
        )
        return TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            created_at=team.created_at.isoformat() if team.created_at else "",
            updated_at=team.updated_at.isoformat() if team.updated_at else "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除团队（仅IT管理员）"""
    try:
        await TeamService.delete_team(db, team_id)
        return {"message": "团队已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 成员管理 ====================

@router.get("/{team_id}/members", response_model=MemberListResponse)
async def list_members(
    team_id: str,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取团队成员列表（仅IT管理员）"""
    members = await TeamService.list_members(db, team_id)
    return MemberListResponse(
        items=[MemberResponse(**m) for m in members],
        total=len(members),
    )


@router.post("/{team_id}/members")
async def add_members(
    team_id: str,
    request: MemberAdd,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """添加团队成员（仅IT管理员）"""
    try:
        added = await TeamService.add_members(
            db, team_id, request.user_ids, request.set_default
        )
        return {"message": f"成功添加 {added} 个成员", "added": added}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: str,
    user_id: str,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """移除团队成员（仅IT管理员）"""
    try:
        await TeamService.remove_member(db, team_id, user_id)
        return {"message": "成员已移除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 助手配置 ====================

@router.get("/{team_id}/config", response_model=ConfigResponse)
async def get_config(
    team_id: str,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取团队配置（仅IT管理员）"""
    config = await TeamService.get_config(db, team_id)
    return ConfigResponse(
        team_id=team_id,
        ragflow_assistant_id=config.ragflow_assistant_id if config else None,
        ragflow_assistant_name=config.ragflow_assistant_name if config else None,
    )


@router.put("/{team_id}/config", response_model=ConfigResponse)
async def bind_assistant(
    team_id: str,
    request: ConfigUpdate,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """绑定助手到团队（仅IT管理员）"""
    try:
        config = await TeamService.bind_assistant(
            db, team_id, request.ragflow_assistant_id
        )
        return ConfigResponse(
            team_id=team_id,
            ragflow_assistant_id=config.ragflow_assistant_id,
            ragflow_assistant_name=config.ragflow_assistant_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 知识库绑定 ====================

@router.get("/{team_id}/datasets", response_model=DatasetListResponse)
async def list_datasets(
    team_id: str,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取团队绑定的知识库列表（仅IT管理员）"""
    datasets = await TeamService.list_datasets(db, team_id)
    return DatasetListResponse(
        items=[
            DatasetItem(
                id=ds.id,
                ragflow_dataset_id=ds.ragflow_dataset_id,
                ragflow_dataset_name=ds.ragflow_dataset_name,
                document_count=ds.document_count,
                chunk_count=ds.chunk_count,
            )
            for ds in datasets
        ],
        total=len(datasets),
    )


@router.put("/{team_id}/datasets", response_model=DatasetListResponse)
async def set_datasets(
    team_id: str,
    request: DatasetBind,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """设置团队知识库绑定（全量替换，仅IT管理员）"""
    try:
        datasets = await TeamService.set_datasets(db, team_id, request.dataset_ids)
        return DatasetListResponse(
            items=[
                DatasetItem(
                    id=ds.id,
                    ragflow_dataset_id=ds.ragflow_dataset_id,
                    ragflow_dataset_name=ds.ragflow_dataset_name,
                    document_count=ds.document_count,
                    chunk_count=ds.chunk_count,
                )
                for ds in datasets
            ],
            total=len(datasets),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
