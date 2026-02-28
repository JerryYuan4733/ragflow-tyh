"""API v1 路由汇总 - 全量"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    health, auth, users, teams, chat, documents, qa,
    stats, settings, announcements, system_feedback,
    ragflow_proxy,
)
from app.api.v1.endpoints.interactions import (
    feedback_router, ticket_router, favorite_router, notification_router,
)

api_router = APIRouter()

# 健康检查 (无需认证)
api_router.include_router(health.router, tags=["健康检查"])

# 认证
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])

# 用户管理
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])

# 团队管理
api_router.include_router(teams.router, prefix="/teams", tags=["团队管理"])

# RAGFlow 代理（供前端拉取助手/知识库列表）
api_router.include_router(ragflow_proxy.router, prefix="/ragflow", tags=["RAGFlow代理"])

# 智能对话
api_router.include_router(chat.router, prefix="/chat", tags=["智能对话"])

# 文档管理
api_router.include_router(documents.router, prefix="/documents", tags=["文档管理"])

# Q&A管理
api_router.include_router(qa.router, prefix="/qa-pairs", tags=["Q&A管理"])

# 反馈
api_router.include_router(feedback_router, prefix="/feedbacks", tags=["反馈"])

# 工单
api_router.include_router(ticket_router, prefix="/tickets", tags=["工单"])

# 收藏
api_router.include_router(favorite_router, prefix="/favorites", tags=["收藏"])

# 通知
api_router.include_router(notification_router, prefix="/notifications", tags=["通知"])

# 统计分析
api_router.include_router(stats.router, prefix="/stats", tags=["统计分析"])

# 系统设置
api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])

# 公告
api_router.include_router(announcements.router, prefix="/announcements", tags=["公告"])

# 系统反馈
api_router.include_router(system_feedback.router, prefix="/system-feedback", tags=["系统反馈"])
