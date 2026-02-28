"""团队管理 Schema (Pydantic DTO)"""

from typing import Optional
from pydantic import BaseModel


# ==================== 团队 CRUD ====================

class TeamCreate(BaseModel):
    """创建团队"""
    name: str
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    """更新团队"""
    name: Optional[str] = None
    description: Optional[str] = None


class TeamResponse(BaseModel):
    """团队响应"""
    id: str
    name: str
    description: Optional[str] = None
    member_count: int = 0
    has_assistant: bool = False
    dataset_count: int = 0
    created_at: str
    updated_at: str


class TeamListResponse(BaseModel):
    """团队列表响应"""
    items: list[TeamResponse]
    total: int
    page: int
    page_size: int


# ==================== 成员管理 ====================

class MemberAdd(BaseModel):
    """添加成员"""
    user_ids: list[str]
    set_default: bool = False


class MemberResponse(BaseModel):
    """成员响应"""
    user_id: str
    username: str
    display_name: str
    role: str
    is_default: bool
    joined_at: str


class MemberListResponse(BaseModel):
    """成员列表响应"""
    items: list[MemberResponse]
    total: int


# ==================== 团队配置（助手绑定） ====================

class ConfigUpdate(BaseModel):
    """绑定助手"""
    ragflow_assistant_id: str


class ConfigResponse(BaseModel):
    """团队配置响应"""
    team_id: str
    ragflow_assistant_id: Optional[str] = None
    ragflow_assistant_name: Optional[str] = None


# ==================== 知识库绑定 ====================

class DatasetBind(BaseModel):
    """绑定知识库（全量替换）"""
    dataset_ids: list[str]


class DatasetItem(BaseModel):
    """知识库条目"""
    id: str
    ragflow_dataset_id: str
    ragflow_dataset_name: Optional[str] = None
    document_count: int = 0
    chunk_count: int = 0


class DatasetListResponse(BaseModel):
    """团队知识库列表响应"""
    items: list[DatasetItem]
    total: int


# ==================== 团队切换 ====================

class ActiveTeamSwitch(BaseModel):
    """切换活跃团队"""
    team_id: str


class MyTeamItem(BaseModel):
    """用户所属团队条目"""
    team_id: str
    team_name: str
    is_default: bool
    is_active: bool


class MyTeamsResponse(BaseModel):
    """用户所属团队列表响应"""
    items: list[MyTeamItem]
    active_team_id: Optional[str] = None
