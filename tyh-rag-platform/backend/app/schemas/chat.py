"""对话 Schema"""

from typing import Optional
from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    title: str = "新对话"


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageRequest(BaseModel):
    content: str
    thinking: bool = False  # FR-39: 是否启用深度思考模式


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[dict] = None
    created_at: str


class SuggestionResponse(BaseModel):
    questions: list[str]


class FeedbackRequest(BaseModel):
    type: str  # like / dislike
    reason_category: Optional[str] = None
    reason_custom: Optional[str] = None
