"""
17张核心表 ORM 模型
基于 architecture.md V1.1 §3.2 ER图 + §3.3 表设计
新增: UserTeam, TeamConfig, TeamDataset (团队知识库绑定)
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Enum, JSON, Float,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ==================== 枚举类型 ====================

class UserRole(str, enum.Enum):
    USER = "user"
    KB_ADMIN = "kb_admin"
    IT_ADMIN = "it_admin"


class TicketStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    VERIFIED = "verified"


class FeedbackType(str, enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class QAStatus(str, enum.Enum):
    """QA 状态枚举"""
    ACTIVE = "active"
    PENDING_REVIEW = "pending_review"
    DISABLED = "disabled"


class QASource(str, enum.Enum):
    """QA 来源枚举"""
    MANUAL = "manual"
    TRANSFER = "transfer"
    RAGFLOW_SYNC = "ragflow_sync"
    IMPORT = "import"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


# ==================== 基础 Mixin ====================

class TimestampMixin:
    """通用时间戳字段"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# ==================== Team ====================

class Team(Base, TimestampMixin):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("name", name="uq_teams_name"),
    )

    # Relationships
    user_teams: Mapped[list["UserTeam"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    config: Mapped[Optional["TeamConfig"]] = relationship(
        back_populates="team", uselist=False, cascade="all, delete-orphan"
    )
    datasets: Mapped[list["TeamDataset"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


# ==================== User ====================

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, values_callable=lambda e: [i.value for i in e]), nullable=False, default=UserRole.USER)
    # active_team_id: 用户当前活跃团队（前端切换用），替代原 team_id 单值外键
    active_team_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    job_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_active_team_id", "active_team_id"),
    )

    # Relationships
    active_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[active_team_id])
    user_teams: Mapped[list["UserTeam"]] = relationship(back_populates="user")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")


# ==================== UserTeam (用户-团队 M:N 关联) ====================

class UserTeam(Base, TimestampMixin):
    """用户-团队关联表，支持 M:N 关系"""
    __tablename__ = "user_teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="uq_user_teams"),
        Index("ix_user_teams_user_id", "user_id"),
        Index("ix_user_teams_team_id", "team_id"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="user_teams")
    team: Mapped["Team"] = relationship(back_populates="user_teams")


# ==================== TeamConfig (团队配置 1:1) ====================

class TeamConfig(Base, TimestampMixin):
    """团队配置表，每个团队绑定唯一一个 RAGFlow 助手"""
    __tablename__ = "team_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    ragflow_assistant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ragflow_assistant_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        UniqueConstraint("team_id", name="uq_team_configs_team"),
    )

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="config")


# ==================== TeamDataset (团队-知识库 1:N) ====================

class TeamDataset(Base, TimestampMixin):
    """团队-知识库关联表，一个团队可绑定多个 RAGFlow 知识库"""
    __tablename__ = "team_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    ragflow_dataset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ragflow_dataset_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("team_id", "ragflow_dataset_id", name="uq_team_datasets"),
        Index("ix_team_datasets_team_id", "team_id"),
    )

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="datasets")


# ==================== Session (对话会话) ====================

class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="新对话", nullable=False)
    ragflow_conversation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_team_id", "team_id"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session")


# ==================== Message ====================

class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, values_callable=lambda e: [i.value for i in e]), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_messages_session_id", "session_id"),
        Index("ix_messages_user_id", "user_id"),
    )

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="messages")
    feedback: Mapped[Optional["Feedback"]] = relationship(back_populates="message", uselist=False)
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="message")


# ==================== Feedback ====================

class Feedback(Base, TimestampMixin):
    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    type: Mapped[FeedbackType] = mapped_column(Enum(FeedbackType, values_callable=lambda e: [i.value for i in e]), nullable=False)
    reason_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason_custom: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_feedbacks_session_id", "session_id"),
        Index("ix_feedbacks_message_id", "message_id"),
        # 同一用户对同一消息只能有一条反馈
        UniqueConstraint("user_id", "message_id", name="uq_feedback_user_message"),
        # 覆盖索引：加速消息历史查询中的 LEFT JOIN
        Index("ix_feedbacks_user_msg", "user_id", "message_id", "type"),
    )

    # Relationships
    message: Mapped["Message"] = relationship(back_populates="feedback")
    ticket: Mapped[Optional["Ticket"]] = relationship(back_populates="feedback", uselist=False)


# ==================== Ticket ====================

class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    feedback_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("feedbacks.id"), nullable=True
    )
    # 关联 QA（转人工创建的工单必须关联 QA，旧工单可为 NULL）
    qa_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("qa_meta.id", ondelete="CASCADE"), nullable=True
    )
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)
    creator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, values_callable=lambda e: [i.value for i in e]), default=TicketStatus.PENDING, nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), default="auto", nullable=False)
    # 触发转人工的消息 ID（用于幂等检查）
    source_message_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_assignee_id", "assignee_id"),
        Index("ix_tickets_creator_id", "creator_id"),
        Index("ix_tickets_qa_id", "qa_id"),
    )

    # Relationships
    feedback: Mapped[Optional["Feedback"]] = relationship(back_populates="ticket")
    qa: Mapped[Optional["QAMeta"]] = relationship(back_populates="ticket")
    logs: Mapped[list["TicketLog"]] = relationship(back_populates="ticket")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="ticket")


# ==================== TicketLog ====================

class TicketLog(Base, TimestampMixin):
    __tablename__ = "ticket_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id"), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    ticket: Mapped["Ticket"] = relationship(back_populates="logs")


# ==================== DocumentMeta ====================

class DocumentMeta(Base, TimestampMixin):
    __tablename__ = "document_meta"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(200), nullable=False)  # MIME type can be very long
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    category_path: Mapped[str] = mapped_column(String(500), default="/", nullable=False)
    ragflow_document_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ragflow_dataset_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    production_document_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ===== 文档状态追踪字段（文档管理功能优化新增）=====

    # 文档状态：uploading/pending/parsing/ready/error
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False,
        comment="文档状态: uploading/pending/parsing/ready/error"
    )
    # RAGFlow 原始 run 值缓存（用于精确状态判断）
    run: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="RAGFlow run 字段缓存: 0/1/2/3/4"
    )
    # 解析进度 0.0 ~ 1.0
    progress: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False,
        comment="解析进度 0.0~1.0"
    )
    # 上次从 RAGFlow 同步的时间
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        comment="上次从 RAGFlow 同步状态的时间"
    )

    __table_args__ = (
        Index("ix_document_meta_team_id", "team_id"),
        Index("ix_document_meta_category", "category_path"),
        # 文档管理功能优化新增索引
        Index("ix_document_meta_ragflow_doc_id", "ragflow_document_id"),
        Index("ix_document_meta_status", "status"),
        Index("ix_document_meta_team_dataset_status", "team_id", "ragflow_dataset_id", "status"),
    )


# ==================== QAMeta ====================

class QAMeta(Base, TimestampMixin):
    __tablename__ = "qa_meta"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    question_summary: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    answer_summary: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ragflow_chunk_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    edited_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # ===== 会话反馈与 QA 工单功能优化新增 =====

    # QA 状态：active/pending_review/disabled
    status: Mapped[QAStatus] = mapped_column(
        Enum(QAStatus, values_callable=lambda e: [i.value for i in e]),
        default=QAStatus.ACTIVE, nullable=False,
        comment="QA 状态: active/pending_review/disabled"
    )
    # QA 来源：manual/transfer/ragflow_sync/import
    source: Mapped[QASource] = mapped_column(
        Enum(QASource, values_callable=lambda e: [i.value for i in e]),
        default=QASource.MANUAL, nullable=False,
        comment="QA 来源: manual/transfer/ragflow_sync/import"
    )
    # 关联的 RAGFlow 知识库 ID
    ragflow_dataset_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="关联的 RAGFlow 知识库 ID"
    )
    # 触发转人工的消息 ID（用于幂等检查）
    source_message_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
        comment="触发转人工的消息 ID"
    )
    # FR-33: 标记 ragflow_sync QA 是否被用户修改过
    is_modified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="是否被用户修改过（用于 ragflow_sync 推送判断）"
    )
    # C-29: 修改 question 前的旧值（推送时查找 RAGFlow 旧 chunk）
    previous_question: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="修改前的旧 question"
    )

    __table_args__ = (
        Index("ix_qa_meta_team_id", "team_id"),
        Index("ix_qa_meta_status", "status"),
        Index("ix_qa_meta_source", "source"),
        Index("ix_qa_meta_dataset_id", "ragflow_dataset_id"),
    )

    # Relationships
    ticket: Mapped[Optional["Ticket"]] = relationship(back_populates="qa", uselist=False)


# ==================== Favorite ====================

class Favorite(Base, TimestampMixin):
    __tablename__ = "favorites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id"), nullable=False)

    __table_args__ = (
        Index("ix_favorites_user_id", "user_id"),
        # 同一用户对同一消息只能收藏一次
        UniqueConstraint("user_id", "message_id", name="uq_favorite_user_message"),
        # 覆盖索引：加速消息历史查询中的 LEFT JOIN
        Index("ix_favorites_user_msg", "user_id", "message_id"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="favorites")
    message: Mapped["Message"] = relationship(back_populates="favorites")


# ==================== Announcement ====================

class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)  # FR-38: 定时发布时间
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)


# ==================== OperationLog ====================

class OperationLog(Base, TimestampMixin):
    __tablename__ = "operation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    __table_args__ = (
        Index("ix_operation_logs_user_id", "user_id"),
        Index("ix_operation_logs_action", "action"),
    )


# ==================== SystemConfig ====================

class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    config_key: Mapped[str] = mapped_column(String(100), nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("config_key", name="uq_system_config_key"),
    )


# ==================== Notification ====================

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    ticket_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("tickets.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_notifications_user_id_read", "user_id", "is_read"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")
    ticket: Mapped[Optional["Ticket"]] = relationship(back_populates="notifications")
