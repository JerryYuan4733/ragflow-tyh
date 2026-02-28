"""
数据迁移脚本: 团队知识库绑定
将现有 users.team_id 数据迁移到 user_teams 关联表 + active_team_id

执行方式:
    cd backend
    uv run python scripts/migrate_team_binding.py

前置条件:
    - 新表 (user_teams, team_configs, team_datasets) 已由 ORM create_all 创建
    - 现有数据库中 users 表仍有 team_id 列
"""

import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

# 将 backend 目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def check_column_exists(session: AsyncSession, table: str, column: str) -> bool:
    """检查表中是否存在指定列"""
    try:
        result = await session.execute(text(
            f"SELECT COUNT(*) FROM information_schema.COLUMNS "
            f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND COLUMN_NAME = :column"
        ), {"table": table, "column": column})
        count = result.scalar()
        return count > 0
    except Exception as e:
        logger.warning(f"检查列 {table}.{column} 是否存在时出错: {e}")
        return False


async def check_table_exists(session: AsyncSession, table: str) -> bool:
    """检查表是否存在"""
    try:
        result = await session.execute(text(
            f"SELECT COUNT(*) FROM information_schema.TABLES "
            f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
        ), {"table": table})
        count = result.scalar()
        return count > 0
    except Exception as e:
        logger.warning(f"检查表 {table} 是否存在时出错: {e}")
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
            # ========== Step 0: 前置检查 ==========
            logger.info("=" * 60)
            logger.info("团队知识库绑定 - 数据迁移脚本")
            logger.info("=" * 60)

            if not await check_table_exists(session, "user_teams"):
                logger.error("user_teams 表不存在，请先启动应用让 ORM 自动创建表")
                return False

            has_team_id = await check_column_exists(session, "users", "team_id")
            if not has_team_id:
                logger.info("users.team_id 列不存在，可能已迁移完成或是全新安装，跳过迁移")
                return True

            # ========== Step 1: 统计待迁移数据 ==========
            result = await session.execute(text(
                "SELECT COUNT(*) FROM users WHERE team_id IS NOT NULL"
            ))
            total_users = result.scalar()
            logger.info(f"Step 1: 发现 {total_users} 条用户记录需迁移 (team_id IS NOT NULL)")

            if total_users == 0:
                logger.info("无数据需要迁移")
                return True

            # ========== Step 2: 迁移 users.team_id → user_teams ==========
            logger.info("Step 2: 迁移 users.team_id → user_teams")

            # 检查是否已有迁移数据（幂等性）
            result = await session.execute(text("SELECT COUNT(*) FROM user_teams"))
            existing_count = result.scalar()
            if existing_count > 0:
                logger.warning(f"user_teams 已有 {existing_count} 条记录，跳过迁移（幂等保护）")
            else:
                if dry_run:
                    logger.info(f"[DRY RUN] 将插入 {total_users} 条 user_teams 记录")
                else:
                    await session.execute(text("""
                        INSERT INTO user_teams (id, user_id, team_id, is_default, created_at, updated_at)
                        SELECT UUID(), id, team_id, TRUE, NOW(), NOW()
                        FROM users
                        WHERE team_id IS NOT NULL
                    """))
                    logger.info(f"已迁移 {total_users} 条用户-团队关联到 user_teams")

            # ========== Step 3: 设置 users.active_team_id ==========
            has_active_team_id = await check_column_exists(session, "users", "active_team_id")
            if has_active_team_id:
                logger.info("Step 3: 设置 users.active_team_id = team_id")
                if dry_run:
                    logger.info(f"[DRY RUN] 将更新 {total_users} 条用户的 active_team_id")
                else:
                    await session.execute(text("""
                        UPDATE users SET active_team_id = team_id
                        WHERE team_id IS NOT NULL AND active_team_id IS NULL
                    """))
                    logger.info("active_team_id 设置完成")
            else:
                logger.warning("users.active_team_id 列不存在，跳过（需先通过 ORM 创建）")

            # ========== Step 4: 迁移全局助手配置 → team_configs ==========
            logger.info("Step 4: 迁移全局助手配置 → 默认团队的 team_configs")
            result = await session.execute(text("SELECT COUNT(*) FROM team_configs"))
            config_count = result.scalar()
            if config_count > 0:
                logger.info(f"team_configs 已有 {config_count} 条记录，跳过")
            else:
                # 尝试从 system_config 读取 knowledge_base 配置
                assistant_id = None
                try:
                    result = await session.execute(text(
                        "SELECT config_value FROM system_config WHERE config_key = 'knowledge_base'"
                    ))
                    row = result.first()
                    if row:
                        kb_config = json.loads(row[0])
                        assistant_id = kb_config.get("assistant_id")
                        logger.info(f"从 system_config 读取到 assistant_id: {assistant_id}")
                except Exception as e:
                    logger.warning(f"读取 system_config.knowledge_base 失败: {e}")

                # 获取默认团队
                result = await session.execute(text(
                    "SELECT id FROM teams ORDER BY created_at ASC LIMIT 1"
                ))
                default_team = result.first()
                if default_team:
                    if dry_run:
                        logger.info(f"[DRY RUN] 将为默认团队 {default_team[0]} 创建 team_configs 记录")
                    else:
                        await session.execute(text("""
                            INSERT INTO team_configs (id, team_id, ragflow_assistant_id, created_at, updated_at)
                            VALUES (:id, :team_id, :assistant_id, NOW(), NOW())
                        """), {
                            "id": str(uuid.uuid4()),
                            "team_id": default_team[0],
                            "assistant_id": assistant_id,
                        })
                        logger.info(f"默认团队 team_configs 已创建 (assistant_id={assistant_id})")

            # ========== Step 5: 验证 ==========
            logger.info("Step 5: 验证迁移结果")
            if not dry_run:
                result = await session.execute(text("SELECT COUNT(*) FROM user_teams"))
                ut_count = result.scalar()

                result = await session.execute(text(
                    "SELECT COUNT(*) FROM users WHERE active_team_id IS NOT NULL"
                ))
                at_count = result.scalar()

                result = await session.execute(text("SELECT COUNT(*) FROM team_configs"))
                tc_count = result.scalar()

                logger.info(f"验证结果:")
                logger.info(f"  user_teams 记录数: {ut_count} (期望: {total_users})")
                logger.info(f"  active_team_id 已设置: {at_count} (期望: {total_users})")
                logger.info(f"  team_configs 记录数: {tc_count}")

                if ut_count < total_users:
                    logger.warning("⚠️ user_teams 记录数少于预期，请检查")
                else:
                    logger.info("✅ 迁移验证通过")

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
    将 user_teams 中 is_default=TRUE 的记录写回 users.team_id
    """
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        try:
            logger.info("开始回滚迁移...")

            has_team_id = await check_column_exists(session, "users", "team_id")
            if not has_team_id:
                logger.error("users.team_id 列已被删除，无法回滚")
                return False

            # 从 user_teams 恢复 team_id
            await session.execute(text("""
                UPDATE users u
                INNER JOIN user_teams ut ON u.id = ut.user_id AND ut.is_default = TRUE
                SET u.team_id = ut.team_id
            """))

            # 清理新表数据
            await session.execute(text("DELETE FROM user_teams"))
            await session.execute(text("DELETE FROM team_configs"))
            await session.execute(text("DELETE FROM team_datasets"))

            # 清除 active_team_id
            has_active_team_id = await check_column_exists(session, "users", "active_team_id")
            if has_active_team_id:
                await session.execute(text("UPDATE users SET active_team_id = NULL"))

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

    parser = argparse.ArgumentParser(description="团队知识库绑定 - 数据迁移脚本")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际修改数据")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.rollback:
        success = asyncio.run(rollback())
    else:
        success = asyncio.run(migrate(dry_run=args.dry_run))

    sys.exit(0 if success else 1)
