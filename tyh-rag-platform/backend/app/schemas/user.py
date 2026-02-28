"""用户管理 Schema (Pydantic DTO)"""

from typing import Optional
from pydantic import BaseModel


class UserCreateRequest(BaseModel):
    """创建用户"""
    username: str
    password: str
    display_name: str
    role: str = "user"
    team_ids: list[str]
    job_number: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """更新用户"""
    display_name: Optional[str] = None
    role: Optional[str] = None
    team_ids: Optional[list[str]] = None
    job_number: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    display_name: str
    role: str
    active_team_id: Optional[str] = None
    active_team_name: Optional[str] = None
    team_ids: list[str] = []
    job_number: Optional[str] = None
    is_active: bool
    created_at: str
    last_login_at: Optional[str] = None


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
