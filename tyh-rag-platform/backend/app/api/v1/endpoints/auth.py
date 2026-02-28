"""认证接口 - 登录/登出/当前用户/团队切换"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User, UserTeam, Team
from app.schemas.auth import LoginRequest, TokenResponse, UserInfoResponse
from app.schemas.team import ActiveTeamSwitch, MyTeamItem, MyTeamsResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录 → 返回 JWT token"""
    result = await db.execute(
        select(User).options(selectinload(User.active_team)).where(User.username == request.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    # 更新最后登录时间
    user.last_login_at = datetime.now(timezone.utc)

    # 生成 JWT
    access_token = create_access_token(data={
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "active_team_id": user.active_team_id,
    })

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role.value,
        active_team_id=user.active_team_id,
        active_team_name=user.active_team.name if user.active_team else None,
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出 (客户端删除token即可)"""
    return {"message": "登出成功"}


@router.get("/me", response_model=UserInfoResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserInfoResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        role=current_user.role.value,
        active_team_id=current_user.active_team_id,
        active_team_name=current_user.active_team.name if current_user.active_team else None,
        is_active=current_user.is_active,
    )


@router.get("/my-teams", response_model=MyTeamsResponse)
async def get_my_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户所属的所有团队"""
    result = await db.execute(
        select(UserTeam, Team)
        .join(Team, UserTeam.team_id == Team.id)
        .where(UserTeam.user_id == current_user.id)
        .order_by(UserTeam.created_at.asc())
    )
    rows = result.all()

    items = [
        MyTeamItem(
            team_id=team.id,
            team_name=team.name,
            is_default=ut.is_default,
            is_active=(team.id == current_user.active_team_id),
        )
        for ut, team in rows
    ]

    return MyTeamsResponse(
        items=items,
        active_team_id=current_user.active_team_id,
    )


@router.post("/switch-team")
async def switch_team(
    request: ActiveTeamSwitch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """切换当前活跃团队"""
    # 验证用户属于目标团队
    result = await db.execute(
        select(UserTeam).where(
            UserTeam.user_id == current_user.id,
            UserTeam.team_id == request.team_id,
        )
    )
    ut = result.scalar_one_or_none()
    if not ut:
        raise HTTPException(
            status_code=403,
            detail="您不属于该团队，无法切换",
        )

    # 更新活跃团队
    current_user.active_team_id = request.team_id
    await db.flush()

    # 获取团队名称
    team_result = await db.execute(select(Team).where(Team.id == request.team_id))
    team = team_result.scalar_one_or_none()

    return {
        "message": "团队切换成功",
        "active_team_id": request.team_id,
        "active_team_name": team.name if team else None,
    }
