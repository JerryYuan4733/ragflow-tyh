"""用户管理接口"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_it_admin
from app.db.session import get_db
from app.models import User, UserTeam
from app.schemas.user import (
    UserCreateRequest, UserUpdateRequest,
    UserResponse, UserListResponse,
)
from app.services.user_service import UserService

router = APIRouter()


def _user_to_response(user: User, team_ids: list[str] | None = None) -> UserResponse:
    """User ORM → DTO"""
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role.value,
        active_team_id=user.active_team_id,
        active_team_name=user.active_team.name if user.active_team else None,
        team_ids=team_ids or [],
        job_number=user.job_number,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    team_id: Optional[str] = None,
    keyword: Optional[str] = None,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表 (仅IT管理员)"""
    users, total = await UserService.get_users(db, page, page_size, team_id, keyword)
    return UserListResponse(
        items=[_user_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request: UserCreateRequest,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建用户 (仅IT管理员)"""
    try:
        user = await UserService.create_user(
            db,
            username=request.username,
            password=request.password,
            display_name=request.display_name,
            role=request.role,
            team_ids=request.team_ids,
            job_number=request.job_number,
        )
        await db.refresh(user, ["active_team"])
        return _user_to_response(user, team_ids=request.team_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新用户 (仅IT管理员)"""
    try:
        user = await UserService.update_user(
            db,
            user_id,
            display_name=request.display_name,
            role=request.role,
            job_number=request.job_number,
        )
        # TODO: 如果 request.team_ids 不为 None，需要更新 user_teams 关联（M3 完善）
        return _user_to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{user_id}/toggle", response_model=UserResponse)
async def toggle_user(
    user_id: str,
    _: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """启用/禁用用户 (仅IT管理员)"""
    try:
        user = await UserService.toggle_user(db, user_id)
        await db.refresh(user, ["active_team"])
        return _user_to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
