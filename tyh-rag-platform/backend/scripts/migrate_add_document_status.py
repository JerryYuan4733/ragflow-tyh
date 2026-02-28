"""
数据迁移脚本: 文档管理功能优化
为 document_meta 表新增 status/run/progress/last_synced_at 字段和索引
在 system_config 表中插入默认解析模式配置

执行方式:
    cd backend
    uv run python scripts/migrate_add_document_status.py

前置条件:
    - document_meta 表已存在
    - system_config 表已存在
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# 将 backend 目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def check_column_exists(session: AsyncSession, table: str, column: str) -> bool:
    """检查表中是否存在指定列"""
    try:
        result = await session.execute(text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND COLUMN_NAME = :column"
        ), {"table": table, "column": column})
        count = result.scalar()
        return count > 0
    except Exception as e:
        logger.warning(f"检查列 {table}.{column} 是否存在时出错: {e}")
        return False


async def check_index_exists(session: AsyncSession, table: str, index_name: str) -> bool:
    """检查索引是否存在"""
    try:
        result = await session.execute(text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND INDEX_NAME = :index_name"
        ), {"table": table, "index_name": index_name})
        count = result.scalar()
        return count > 0
    except Exception as e:
        logger.warning(f"检查索引 {table}.{index_name} 是否存在时出错: {e}")
        return False


async def migrate(dry_run: bool = False):
    """
    执行迁移

    Args:
        dry_run: 仅打印将执行的操作，不实际修改数据
    """
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        try:
            logger.info("=" * 60)
            logger.info("文档管理功能优化 - 数据迁移脚本")
            logger.info("=" * 60)

            # ========== Step 1: 新增 4 个字段 ==========
            logger.info("Step 1: 新增 document_meta 字段")

            columns_to_add = [
                ("status", "VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '文档状态: uploading/pending/parsing/ready/error'"),
                ("run", "VARCHAR(20) NULL COMMENT 'RAGFlow run 字段缓存: 0/1/2/3/4'"),
                ("progress", "FLOAT NOT NULL DEFAULT 0.0 COMMENT '解析进度 0.0~1.0'"),
                ("last_synced_at", "DATETIME NULL COMMENT '上次从 RAGFlow 同步状态的时间'"),
            ]

            for col_name, col_def in columns_to_add:
                exists = await check_column_exists(session, "document_meta", col_name)
                if exists:
                    logger.info(f"  列 {col_name} 已存在，跳过")
                else:
                    if dry_run:
                        logger.info(f"  [DRY RUN] 将新增列 {col_name}")
                    else:
                        await session.execute(text(
                            f"ALTER TABLE document_meta ADD COLUMN {col_name} {col_def}"
                        ))
                        logger.info(f"  已新增列 {col_name}")

            # ========== Step 2: 新增 3 个索引 ==========
            logger.info("Step 2: 新增索引")

            indexes_to_add = [
                ("ix_document_meta_ragflow_doc_id", "CREATE INDEX ix_document_meta_ragflow_doc_id ON document_meta (ragflow_document_id)"),
                ("ix_document_meta_status", "CREATE INDEX ix_document_meta_status ON document_meta (status)"),
                ("ix_document_meta_team_dataset_status", "CREATE INDEX ix_document_meta_team_dataset_status ON document_meta (team_id, ragflow_dataset_id, status)"),
            ]

            for idx_name, idx_sql in indexes_to_add:
                exists = await check_index_exists(session, "document_meta", idx_name)
                if exists:
                    logger.info(f"  索引 {idx_name} 已存在，跳过")
                else:
                    if dry_run:
                        logger.info(f"  [DRY RUN] 将创建索引 {idx_name}")
                    else:
                        await session.execute(text(idx_sql))
                        logger.info(f"  已创建索引 {idx_name}")

            # ========== Step 3: 初始化现有记录状态 ==========
            logger.info("Step 3: 初始化现有记录状态")

            # 统计待更新记录
            result = await session.execute(text("SELECT COUNT(*) FROM document_meta"))
            total_docs = result.scalar()
            logger.info(f"  document_meta 共 {total_docs} 条记录")

            if total_docs > 0:
                # 检查 status 列是否已存在（dry-run 模式下可能还未添加）
                status_col_exists = await check_column_exists(session, "document_meta", "status")

                if status_col_exists:
                    # 列已存在，按 status='pending' 精确统计
                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM document_meta "
                        "WHERE ragflow_document_id IS NOT NULL AND status = 'pending'"
                    ))
                    ready_count = result.scalar()

                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM document_meta "
                        "WHERE ragflow_document_id IS NULL AND status = 'pending'"
                    ))
                    error_count = result.scalar()
                else:
                    # 列尚未添加（dry-run），用不依赖新列的查询估算
                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM document_meta WHERE ragflow_document_id IS NOT NULL"
                    ))
                    ready_count = result.scalar()

                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM document_meta WHERE ragflow_document_id IS NULL"
                    ))
                    error_count = result.scalar()

                if dry_run:
                    logger.info(f"  [DRY RUN] 将设置 {ready_count} 条记录 status='ready'（有 ragflow_document_id）")
                    logger.info(f"  [DRY RUN] 将设置 {error_count} 条记录 status='error'（无 ragflow_document_id）")
                else:
                    await session.execute(text(
                        "UPDATE document_meta SET status = 'ready' "
                        "WHERE ragflow_document_id IS NOT NULL AND status = 'pending'"
                    ))
                    logger.info(f"  已设置 {ready_count} 条记录 status='ready'")

                    await session.execute(text(
                        "UPDATE document_meta SET status = 'error' "
                        "WHERE ragflow_document_id IS NULL AND status = 'pending'"
                    ))
                    logger.info(f"  已设置 {error_count} 条记录 status='error'")

            # ========== Step 4: 插入默认解析模式配置 ==========
            logger.info("Step 4: 插入默认解析模式配置")

            result = await session.execute(text(
                "SELECT COUNT(*) FROM system_config WHERE config_key = 'default_parse_mode'"
            ))
            config_exists = result.scalar() > 0

            if config_exists:
                logger.info("  default_parse_mode 配置已存在，跳过")
            else:
                if dry_run:
                    logger.info("  [DRY RUN] 将插入 default_parse_mode='auto'")
                else:
                    # 获取一个管理员用户 ID 作为 updated_by
                    result = await session.execute(text(
                        "SELECT id FROM users WHERE role = 'it_admin' ORDER BY created_at ASC LIMIT 1"
                    ))
                    admin = result.first()
                    updated_by = admin[0] if admin else "system"

                    await session.execute(text(
                        "INSERT INTO system_config (id, config_key, config_value, updated_by, created_at, updated_at) "
                        "VALUES (:id, 'default_parse_mode', '\"auto\"', :updated_by, NOW(), NOW())"
                    ), {"id": str(uuid.uuid4()), "updated_by": updated_by})
                    logger.info("  已插入 default_parse_mode='auto'")

            # ========== Step 5: 验证 ==========
            logger.info("Step 5: 验证迁移结果")
            if not dry_run:
                # 验证字段存在
                for col_name, _ in columns_to_add:
                    exists = await check_column_exists(session, "document_meta", col_name)
                    status_icon = "✅" if exists else "❌"
                    logger.info(f"  {status_icon} 列 {col_name}: {'存在' if exists else '不存在'}")

                # 验证索引存在
                for idx_name, _ in indexes_to_add:
                    exists = await check_index_exists(session, "document_meta", idx_name)
                    status_icon = "✅" if exists else "❌"
                    logger.info(f"  {status_icon} 索引 {idx_name}: {'存在' if exists else '不存在'}")

                # 验证状态分布
                result = await session.execute(text(
                    "SELECT status, COUNT(*) as cnt FROM document_meta GROUP BY status"
                ))
                rows = result.all()
                logger.info("  文档状态分布:")
                for row in rows:
                    logger.info(f"    {row[0]}: {row[1]}")

                # 验证配置
                result = await session.execute(text(
                    "SELECT config_value FROM system_config WHERE config_key = 'default_parse_mode'"
                ))
                config_row = result.first()
                if config_row:
                    logger.info(f"  ✅ default_parse_mode = {config_row[0]}")
                else:
                    logger.warning("  ❌ default_parse_mode 配置不存在")

            # 提交事务
            if not dry_run:
                await session.commit()
                logger.info("事务已提交")
            else:
                await session.rollback()
                logger.info("[DRY RUN] 事务已回滚（仅预览模式）")

            logger.info("=" * 60)
            logger.info("迁移完成")
            logger.info("=" * 60)
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"迁移失败，已回滚: {e}", exc_info=True)
            return False

    await engine.dispose()


async def rollback():
    """
    回滚迁移（紧急情况使用）
    删除新增的字段、索引和配置项
    """
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        try:
            logger.info("开始回滚迁移...")

            # 删除索引（先删索引再删列）
            indexes_to_drop = [
                "ix_document_meta_ragflow_doc_id",
                "ix_document_meta_status",
                "ix_document_meta_team_dataset_status",
            ]
            for idx_name in indexes_to_drop:
                exists = await check_index_exists(session, "document_meta", idx_name)
                if exists:
                    await session.execute(text(f"DROP INDEX {idx_name} ON document_meta"))
                    logger.info(f"  已删除索引 {idx_name}")

            # 删除字段
            columns_to_drop = ["status", "run", "progress", "last_synced_at"]
            for col_name in columns_to_drop:
                exists = await check_column_exists(session, "document_meta", col_name)
                if exists:
                    await session.execute(text(f"ALTER TABLE document_meta DROP COLUMN {col_name}"))
                    logger.info(f"  已删除列 {col_name}")

            # 删除配置项
            await session.execute(text(
                "DELETE FROM system_config WHERE config_key = 'default_parse_mode'"
            ))
            logger.info("  已删除 default_parse_mode 配置")

            await session.commit()
            logger.info("回滚完成")
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"回滚失败: {e}", exc_info=True)
            return False

    await engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="文档管理功能优化 - 数据迁移脚本")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际修改数据")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.rollback:
        success = asyncio.run(rollback())
    else:
        success = asyncio.run(migrate(dry_run=args.dry_run))

    sys.exit(0 if success else 1)
