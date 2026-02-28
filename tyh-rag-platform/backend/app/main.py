"""AI知识库系统 - FastAPI 主入口"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.api.v1.router import api_router

# 全局日志配置：确保应用层 logger.info() 可见
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import logging
    from sqlalchemy import text
    from app.db.session import async_session_factory, engine, Base
    
    logger = logging.getLogger(__name__)
    
    # ========== 1. 自动创建数据库表 ==========
    try:
        from app.models import (
            Team, User, UserTeam, TeamConfig, TeamDataset,
            Session, Message, Feedback, Ticket, TicketLog,
            DocumentMeta, QAMeta, Favorite, Announcement, OperationLog,
            SystemConfig, Notification
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表检查/创建完成")
    except Exception as e:
        logger.warning(f"数据库表创建失败: {e}")
    
    # ========== 1.5 自动迁移：为已有表添加新列 ==========
    try:
        async with engine.begin() as conn:
            # teams 表新增 description 列
            try:
                await conn.execute(text(
                    "ALTER TABLE teams ADD COLUMN description VARCHAR(500) DEFAULT NULL"
                ))
                logger.info("Auto-migration: teams.description 列已添加")
            except Exception:
                pass  # 列已存在

            # users 表新增 active_team_id 列（替代旧的 team_id）
            try:
                await conn.execute(text(
                    "ALTER TABLE users ADD COLUMN active_team_id VARCHAR(36) DEFAULT NULL"
                ))
                logger.info("Auto-migration: users.active_team_id 列已添加")
            except Exception:
                pass  # 列已存在

            # 如果旧的 team_id 列还存在，将数据迁移到 active_team_id
            try:
                await conn.execute(text(
                    "UPDATE users SET active_team_id = team_id WHERE active_team_id IS NULL AND team_id IS NOT NULL"
                ))
                logger.info("Auto-migration: users.team_id → active_team_id 数据迁移完成")
            except Exception:
                pass  # team_id 列不存在或已迁移

            # 将旧的 team_id 列改为可空（避免阻塞新用户插入）
            try:
                await conn.execute(text(
                    "ALTER TABLE users MODIFY COLUMN team_id VARCHAR(36) DEFAULT NULL"
                ))
                logger.info("Auto-migration: users.team_id 已改为可空")
            except Exception:
                pass  # team_id 列不存在或已可空

            # 为已有用户补建 user_teams 关联记录（有 active_team_id 但无 user_teams 记录）
            try:
                await conn.execute(text("""
                    INSERT IGNORE INTO user_teams (id, user_id, team_id, is_default, created_at, updated_at)
                    SELECT UUID(), u.id, u.active_team_id, 1, NOW(), NOW()
                    FROM users u
                    WHERE u.active_team_id IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM user_teams ut
                          WHERE ut.user_id = u.id AND ut.team_id = u.active_team_id
                      )
                """))
                logger.info("Auto-migration: user_teams 关联记录已补建")
            except Exception as e2:
                logger.debug(f"user_teams 补建跳过: {e2}")

            # 为已有团队补建 team_configs 记录（无配置的团队）
            try:
                await conn.execute(text("""
                    INSERT IGNORE INTO team_configs (id, team_id, created_at, updated_at)
                    SELECT UUID(), t.id, NOW(), NOW()
                    FROM teams t
                    WHERE NOT EXISTS (
                        SELECT 1 FROM team_configs tc WHERE tc.team_id = t.id
                    )
                """))
                logger.info("Auto-migration: team_configs 记录已补建")
            except Exception as e3:
                logger.debug(f"team_configs 补建跳过: {e3}")

            # 为所有IT管理员补建与所有团队的 user_teams 关联
            try:
                await conn.execute(text("""
                    INSERT IGNORE INTO user_teams (id, user_id, team_id, is_default, created_at, updated_at)
                    SELECT UUID(), u.id, t.id, 0, NOW(), NOW()
                    FROM users u
                    CROSS JOIN teams t
                    WHERE u.role = 'it_admin'
                      AND NOT EXISTS (
                          SELECT 1 FROM user_teams ut
                          WHERE ut.user_id = u.id AND ut.team_id = t.id
                      )
                """))
                logger.info("Auto-migration: IT管理员已补建到所有团队")
            except Exception as e4:
                logger.debug(f"IT管理员补建跳过: {e4}")
    except Exception as e:
        logger.warning(f"自动迁移失败: {e}")

    # ========== 1.6 Auto-migration: document_meta 文档状态字段 ==========
    try:
        async with engine.begin() as conn:
            # 新增 status 列
            try:
                await conn.execute(text(
                    "ALTER TABLE document_meta ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending' "
                    "COMMENT '文档状态: uploading/pending/parsing/ready/error'"
                ))
                logger.info("Auto-migration: document_meta.status 列已添加")
            except Exception:
                pass  # 列已存在

            # 新增 run 列
            try:
                await conn.execute(text(
                    "ALTER TABLE document_meta ADD COLUMN run VARCHAR(20) NULL "
                    "COMMENT 'RAGFlow run 字段缓存: 0/1/2/3/4'"
                ))
                logger.info("Auto-migration: document_meta.run 列已添加")
            except Exception:
                pass

            # 新增 progress 列
            try:
                await conn.execute(text(
                    "ALTER TABLE document_meta ADD COLUMN progress FLOAT NOT NULL DEFAULT 0.0 "
                    "COMMENT '解析进度 0.0~1.0'"
                ))
                logger.info("Auto-migration: document_meta.progress 列已添加")
            except Exception:
                pass

            # 新增 last_synced_at 列
            try:
                await conn.execute(text(
                    "ALTER TABLE document_meta ADD COLUMN last_synced_at DATETIME NULL "
                    "COMMENT '上次从 RAGFlow 同步状态的时间'"
                ))
                logger.info("Auto-migration: document_meta.last_synced_at 列已添加")
            except Exception:
                pass

            # 新增索引（忽略已存在错误）
            for idx_name, idx_sql in [
                ("ix_document_meta_ragflow_doc_id",
                 "CREATE INDEX ix_document_meta_ragflow_doc_id ON document_meta (ragflow_document_id)"),
                ("ix_document_meta_status",
                 "CREATE INDEX ix_document_meta_status ON document_meta (status)"),
                ("ix_document_meta_team_dataset_status",
                 "CREATE INDEX ix_document_meta_team_dataset_status ON document_meta (team_id, ragflow_dataset_id, status)"),
            ]:
                try:
                    await conn.execute(text(idx_sql))
                    logger.info(f"Auto-migration: 索引 {idx_name} 已创建")
                except Exception:
                    pass  # 索引已存在

            # 初始化现有记录：有 ragflow_document_id 的设为 ready，无的设为 error
            try:
                await conn.execute(text(
                    "UPDATE document_meta SET status = 'ready' "
                    "WHERE ragflow_document_id IS NOT NULL AND status = 'pending'"
                ))
                await conn.execute(text(
                    "UPDATE document_meta SET status = 'error' "
                    "WHERE ragflow_document_id IS NULL AND status = 'pending'"
                ))
                logger.info("Auto-migration: document_meta 现有记录状态已初始化")
            except Exception as e5:
                logger.debug(f"document_meta 状态初始化跳过: {e5}")
    except Exception as e:
        logger.warning(f"document_meta 自动迁移失败: {e}")

    # ========== 1.7 Auto-migration: 会话反馈与 QA 工单功能优化 ==========
    try:
        async with engine.begin() as conn:
            # --- T-2.1: qa_meta 新增 4 个字段 ---
            for col_name, col_def in [
                ("status", "VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT 'QA 状态: active/pending_review/disabled'"),
                ("source", "VARCHAR(20) NOT NULL DEFAULT 'manual' COMMENT 'QA 来源: manual/transfer/ragflow_sync/import'"),
                ("ragflow_dataset_id", "VARCHAR(100) NULL COMMENT '关联的 RAGFlow 知识库 ID'"),
                ("source_message_id", "VARCHAR(36) NULL COMMENT '触发转人工的消息 ID'"),
            ]:
                try:
                    await conn.execute(text(
                        f"ALTER TABLE qa_meta ADD COLUMN {col_name} {col_def}"
                    ))
                    logger.info(f"Auto-migration: qa_meta.{col_name} 列已添加")
                except Exception:
                    pass  # 列已存在

            # --- T-2.2: tickets 新增 2 个字段 ---
            for col_name, col_def in [
                ("qa_id", "VARCHAR(36) NULL COMMENT '关联 QA ID'"),
                ("source_message_id", "VARCHAR(36) NULL COMMENT '触发转人工的消息 ID'"),
            ]:
                try:
                    await conn.execute(text(
                        f"ALTER TABLE tickets ADD COLUMN {col_name} {col_def}"
                    ))
                    logger.info(f"Auto-migration: tickets.{col_name} 列已添加")
                except Exception:
                    pass

            # --- T-2.5: 旧 feedbacks 去重（保留最新，按 created_at DESC） ---
            try:
                await conn.execute(text("""
                    DELETE f1 FROM feedbacks f1
                    INNER JOIN feedbacks f2
                        ON f1.user_id = f2.user_id
                        AND f1.message_id = f2.message_id
                        AND f1.created_at < f2.created_at
                """))
                logger.info("Auto-migration: feedbacks 旧重复记录已清理")
            except Exception as e_dup:
                logger.debug(f"feedbacks 去重跳过: {e_dup}")

            # --- T-2.6: 旧 favorites 去重 ---
            try:
                await conn.execute(text("""
                    DELETE f1 FROM favorites f1
                    INNER JOIN favorites f2
                        ON f1.user_id = f2.user_id
                        AND f1.message_id = f2.message_id
                        AND f1.created_at < f2.created_at
                """))
                logger.info("Auto-migration: favorites 旧重复记录已清理")
            except Exception as e_dup:
                logger.debug(f"favorites 去重跳过: {e_dup}")

            # --- T-2.7: 唯一约束（跳过已存在） ---
            for constraint_sql in [
                "ALTER TABLE feedbacks ADD CONSTRAINT uq_feedback_user_message UNIQUE (user_id, message_id)",
                "ALTER TABLE favorites ADD CONSTRAINT uq_favorite_user_message UNIQUE (user_id, message_id)",
            ]:
                try:
                    await conn.execute(text(constraint_sql))
                    logger.info(f"Auto-migration: 唯一约束已添加")
                except Exception:
                    pass  # 约束已存在

            # --- T-2.7: 外键 tickets.qa_id → qa_meta.id ON DELETE CASCADE ---
            try:
                await conn.execute(text(
                    "ALTER TABLE tickets ADD CONSTRAINT fk_tickets_qa_id "
                    "FOREIGN KEY (qa_id) REFERENCES qa_meta(id) ON DELETE CASCADE"
                ))
                logger.info("Auto-migration: tickets.qa_id 外键已添加")
            except Exception:
                pass  # 外键已存在

            # --- T-2.8: 新增索引（覆盖索引 + qa_meta 索引） ---
            for idx_name, idx_sql in [
                ("ix_feedbacks_user_msg",
                 "CREATE INDEX ix_feedbacks_user_msg ON feedbacks (user_id, message_id, type)"),
                ("ix_favorites_user_msg",
                 "CREATE INDEX ix_favorites_user_msg ON favorites (user_id, message_id)"),
                ("ix_qa_meta_status",
                 "CREATE INDEX ix_qa_meta_status ON qa_meta (status)"),
                ("ix_qa_meta_source",
                 "CREATE INDEX ix_qa_meta_source ON qa_meta (source)"),
                ("ix_qa_meta_dataset_id",
                 "CREATE INDEX ix_qa_meta_dataset_id ON qa_meta (ragflow_dataset_id)"),
                ("ix_tickets_qa_id",
                 "CREATE INDEX ix_tickets_qa_id ON tickets (qa_id)"),
            ]:
                try:
                    await conn.execute(text(idx_sql))
                    logger.info(f"Auto-migration: 索引 {idx_name} 已创建")
                except Exception:
                    pass  # 索引已存在

        logger.info("Auto-migration: 会话反馈与 QA 工单功能优化迁移完成")
    except Exception as e:
        logger.warning(f"会话反馈与 QA 工单功能优化迁移失败: {e}")

    # ========== 1.8 Auto-migration: QA推送优化 (FR-32/33/34) ==========
    try:
        async with engine.begin() as conn:
            # FR-33/C-25: qa_meta 新增 is_modified 字段
            try:
                await conn.execute(text(
                    "ALTER TABLE qa_meta ADD COLUMN is_modified BOOLEAN NOT NULL DEFAULT FALSE "
                    "COMMENT '是否被用户修改过（用于 ragflow_sync 推送判断）'"
                ))
                logger.info("Auto-migration: qa_meta.is_modified 列已添加")
            except Exception:
                pass  # 列已存在

            # C-29: qa_meta 新增 previous_question 字段
            try:
                await conn.execute(text(
                    "ALTER TABLE qa_meta ADD COLUMN previous_question TEXT NULL "
                    "COMMENT '修改前的旧 question'"
                ))
                logger.info("Auto-migration: qa_meta.previous_question 列已添加")
            except Exception:
                pass  # 列已存在

            # 补偿: 迁移前已编辑的 ragflow_sync QA 需标记 is_modified=True
            result = await conn.execute(text(
                "UPDATE qa_meta SET is_modified = TRUE "
                "WHERE source = 'ragflow_sync' AND version > 1 AND is_modified = FALSE"
            ))
            if result.rowcount > 0:
                logger.info(
                    f"Auto-migration: 补偿标记 {result.rowcount} 条已编辑的 ragflow_sync QA"
                )

        logger.info("Auto-migration: QA推送优化迁移完成")
    except Exception as e:
        logger.warning(f"QA推送优化迁移失败: {e}")

    # ========== 1.9 Auto-migration: FR-38 公告管理增强 ==========
    try:
        async with engine.begin() as conn:
            # FR-38: announcements 新增 scheduled_at 定时发布字段
            try:
                await conn.execute(text(
                    "ALTER TABLE announcements ADD COLUMN scheduled_at DATETIME DEFAULT NULL "
                    "COMMENT 'FR-38: 定时发布时间'"
                ))
                logger.info("Auto-migration: announcements.scheduled_at 列已添加")
            except Exception:
                pass  # 列已存在
        logger.info("Auto-migration: FR-38 公告管理增强迁移完成")
    except Exception as e:
        logger.warning(f"FR-38 公告管理增强迁移失败: {e}")

    # ========== 2. 自动创建默认团队和管理员 ==========
    try:
        from app.models import Team, User, UserTeam, TeamConfig, UserRole
        from sqlalchemy import select
        import uuid
        import bcrypt
        
        async with async_session_factory() as db:
            # 检查是否已有团队
            result = await db.execute(select(Team).limit(1))
            if not result.scalar_one_or_none():
                # 创建默认团队
                team_id = str(uuid.uuid4())
                team = Team(id=team_id, name="默认团队", description="系统默认团队")
                db.add(team)
                
                # 创建默认团队配置（空助手，待IT管理员绑定）
                team_config = TeamConfig(
                    id=str(uuid.uuid4()),
                    team_id=team_id,
                )
                db.add(team_config)
                
                # 创建管理员
                admin_id = str(uuid.uuid4())
                admin = User(
                    id=admin_id,
                    username="admin",
                    password_hash=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8"),
                    display_name="系统管理员",
                    role=UserRole.IT_ADMIN,
                    active_team_id=team_id,
                    is_active=True,
                )
                db.add(admin)
                
                # 创建用户-团队关联
                user_team = UserTeam(
                    id=str(uuid.uuid4()),
                    user_id=admin_id,
                    team_id=team_id,
                    is_default=True,
                )
                db.add(user_team)
                
                await db.commit()
                logger.info("默认团队和管理员已创建: admin / admin123")
            else:
                logger.info("默认数据已存在，跳过初始化")
    except Exception as e:
        logger.warning(f"默认数据创建失败: {e}")
    
    # ========== 3. 加载 RAGFlow 连接配置 ==========
    try:
        from app.api.v1.endpoints.settings import load_ragflow_connection_from_db
        async with async_session_factory() as db:
            await load_ragflow_connection_from_db(db)
    except Exception as e:
        logger.warning(f"加载 RAGFlow 连接配置失败: {e}")

    # ========== 3.1 加载文档解析配置到内存缓存 ==========
    try:
        from app.api.v1.endpoints.settings import load_parse_config_from_db
        async with async_session_factory() as db:
            await load_parse_config_from_db(db)
    except Exception as e:
        logger.warning(f"加载文档解析配置失败: {e}")

    # ========== 4. Auto-migration: 扩展 file_type 列 ==========
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE document_meta MODIFY COLUMN file_type VARCHAR(200) NOT NULL"))
        logger.info("Auto-migration: file_type expanded to VARCHAR(200)")
    except Exception:
        pass  # 可能已经是200或表不存在

    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI知识库系统 - 基于RAGflow的智能问答平台",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由注册
app.include_router(api_router, prefix="/api/v1")

# 前端静态文件挂载 (生产环境)
static_dir = Path("/app/static")
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 路由回退 - 所有非API路径返回 index.html"""
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"detail": "Frontend not built"}
