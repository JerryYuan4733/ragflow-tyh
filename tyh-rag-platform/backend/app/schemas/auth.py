"""认证 Schema (Pydantic DTO)"""

from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """登录成功响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    display_name: str
    role: str
    active_team_id: Optional[str] = None
    active_team_name: Optional[str] = None


class UserInfoResponse(BaseModel):
    """当前用户信息"""
    id: str
    username: str
    display_name: str
    role: str
    active_team_id: Optional[str] = None
    active_team_name: Optional[str] = None
    is_active: bool
