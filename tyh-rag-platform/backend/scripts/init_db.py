"""
数据库初始化脚本
在 RAGFlow MySQL 中创建 knowledge_base 数据库和所有表
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiomysql
from sqlalchemy import text


async def create_database():
    """创建 knowledge_base 数据库"""
    # 从环境变量或默认配置获取连接信息
    import os
    db_url = os.getenv("DATABASE_URL", "mysql+aiomysql://root:infini_rag_flow@127.0.0.1:5455/knowledge_base")
    
    # 解析连接信息
    # mysql+aiomysql://user:password@host:port/database
    parts = db_url.replace("mysql+aiomysql://", "").split("@")
    user_pass = parts[0].split(":")
    host_port_db = parts[1].split("/")
    host_port = host_port_db[0].split(":")
    
    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ""
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    database = host_port_db[1] if len(host_port_db) > 1 else "knowledge_base"
    
    print(f"连接 MySQL: {host}:{port} (用户: {user})")
    
    # 连接 MySQL（不指定数据库）
    conn = await aiomysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
    )
    
    async with conn.cursor() as cursor:
        # 创建数据库
        await cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{database}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        print(f"✓ 数据库 '{database}' 已创建或已存在")
    
    conn.close()
    return database


async def create_tables():
    """创建所有表"""
    from app.db.session import engine, Base
    from app.models import (
        Team, User, Session, Message, Feedback, Ticket, TicketLog,
        DocumentMeta, QAMeta, Favorite, Announcement, OperationLog,
        SystemConfig, Notification
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✓ 所有表已创建")


async def create_default_data():
    """创建默认数据（团队和管理员）"""
    import uuid
    from passlib.context import CryptContext
    from app.db.session import async_session_factory
    from app.models import Team, User, UserRole
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async with async_session_factory() as session:
        # 检查是否已存在数据
        from sqlalchemy import select
        result = await session.execute(select(Team).limit(1))
        if result.scalar_one_or_none():
            print("✓ 默认数据已存在，跳过")
            return
        
        # 创建默认团队
        team_id = str(uuid.uuid4())
        team = Team(id=team_id, name="默认团队")
        session.add(team)
        
        # 创建管理员用户
        admin_id = str(uuid.uuid4())
        admin = User(
            id=admin_id,
            username="admin",
            password_hash=pwd_context.hash("admin123"),
            display_name="系统管理员",
            role=UserRole.IT_ADMIN,
            team_id=team_id,
            is_active=True,
        )
        session.add(admin)
        
        # 创建知识库管理员
        kb_admin_id = str(uuid.uuid4())
        kb_admin = User(
            id=kb_admin_id,
            username="kb_admin",
            password_hash=pwd_context.hash("admin123"),
            display_name="知识库管理员",
            role=UserRole.KB_ADMIN,
            team_id=team_id,
            is_active=True,
        )
        session.add(kb_admin)
        
        # 创建普通用户
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username="user",
            password_hash=pwd_context.hash("user123"),
            display_name="普通用户",
            role=UserRole.USER,
            team_id=team_id,
            is_active=True,
        )
        session.add(user)
        
        await session.commit()
        print("✓ 默认数据已创建:")
        print("  - 团队: 默认团队")
        print("  - 管理员: admin / admin123")
        print("  - KB管理员: kb_admin / admin123")
        print("  - 普通用户: user / user123")


async def main():
    print("=" * 50)
    print("tyh-rag-platform 数据库初始化")
    print("=" * 50)
    
    # 1. 创建数据库
    await create_database()
    
    # 2. 创建表
    await create_tables()
    
    # 3. 创建默认数据
    await create_default_data()
    
    print("=" * 50)
    print("✓ 初始化完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
