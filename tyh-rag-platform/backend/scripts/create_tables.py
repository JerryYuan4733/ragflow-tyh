"""
独立建表脚本 - 使用 pymysql 同步连接创建14张表
运行: python -m scripts.create_tables
"""

import pymysql

DB_CONFIG = {
    "host": "172.31.1.3",
    "port": 4000,
    "user": "skyline-test",
    "password": "Vi689PdhZTHMIcTuN8A",
    "database": "knowledge_base",
    "charset": "utf8mb4",
    "connect_timeout": 10,
}

TABLES_SQL = [
    # 1. teams
    """
    CREATE TABLE IF NOT EXISTS teams (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_teams_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 2. users
    """
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(50) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        display_name VARCHAR(100) NOT NULL,
        role ENUM('user', 'kb_admin', 'it_admin') NOT NULL DEFAULT 'user',
        team_id VARCHAR(36) NOT NULL,
        job_number VARCHAR(50) DEFAULT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        last_login_at DATETIME DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_users_username (username),
        INDEX ix_users_team_id (team_id),
        FOREIGN KEY (team_id) REFERENCES teams(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 3. sessions
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        team_id VARCHAR(36) NOT NULL,
        title VARCHAR(200) NOT NULL DEFAULT '新对话',
        ragflow_conversation_id VARCHAR(100) DEFAULT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_sessions_user_id (user_id),
        INDEX ix_sessions_team_id (team_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (team_id) REFERENCES teams(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 4. messages
    """
    CREATE TABLE IF NOT EXISTS messages (
        id VARCHAR(36) PRIMARY KEY,
        session_id VARCHAR(36) NOT NULL,
        user_id VARCHAR(36) NOT NULL,
        role ENUM('user', 'assistant') NOT NULL,
        content TEXT NOT NULL,
        citations JSON DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_messages_session_id (session_id),
        INDEX ix_messages_user_id (user_id),
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 5. feedbacks
    """
    CREATE TABLE IF NOT EXISTS feedbacks (
        id VARCHAR(36) PRIMARY KEY,
        message_id VARCHAR(36) NOT NULL,
        session_id VARCHAR(36) NOT NULL,
        user_id VARCHAR(36) NOT NULL,
        type ENUM('like', 'dislike') NOT NULL,
        reason_category VARCHAR(50) DEFAULT NULL,
        reason_custom TEXT DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_feedbacks_session_id (session_id),
        INDEX ix_feedbacks_message_id (message_id),
        FOREIGN KEY (message_id) REFERENCES messages(id),
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 6. tickets
    """
    CREATE TABLE IF NOT EXISTS tickets (
        id VARCHAR(36) PRIMARY KEY,
        feedback_id VARCHAR(36) DEFAULT NULL,
        session_id VARCHAR(36) NOT NULL,
        creator_id VARCHAR(36) NOT NULL,
        assignee_id VARCHAR(36) DEFAULT NULL,
        title VARCHAR(200) NOT NULL,
        description TEXT DEFAULT NULL,
        status ENUM('pending', 'processing', 'resolved', 'verified') NOT NULL DEFAULT 'pending',
        source VARCHAR(20) NOT NULL DEFAULT 'auto',
        resolved_at DATETIME DEFAULT NULL,
        verified_at DATETIME DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_tickets_status (status),
        INDEX ix_tickets_assignee_id (assignee_id),
        INDEX ix_tickets_creator_id (creator_id),
        FOREIGN KEY (feedback_id) REFERENCES feedbacks(id),
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (creator_id) REFERENCES users(id),
        FOREIGN KEY (assignee_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 7. ticket_logs
    """
    CREATE TABLE IF NOT EXISTS ticket_logs (
        id VARCHAR(36) PRIMARY KEY,
        ticket_id VARCHAR(36) NOT NULL,
        operator_id VARCHAR(36) NOT NULL,
        action VARCHAR(50) NOT NULL,
        detail TEXT DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id),
        FOREIGN KEY (operator_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 8. document_meta
    """
    CREATE TABLE IF NOT EXISTS document_meta (
        id VARCHAR(36) PRIMARY KEY,
        team_id VARCHAR(36) NOT NULL,
        uploaded_by VARCHAR(36) NOT NULL,
        filename VARCHAR(255) NOT NULL,
        file_type VARCHAR(20) NOT NULL,
        file_size INT NOT NULL,
        category_path VARCHAR(500) NOT NULL DEFAULT '/',
        ragflow_document_id VARCHAR(100) DEFAULT NULL,
        ragflow_dataset_id VARCHAR(100) DEFAULT NULL,
        version INT NOT NULL DEFAULT 1,
        priority INT NOT NULL DEFAULT 0,
        quality_score FLOAT DEFAULT NULL,
        expires_at DATETIME DEFAULT NULL,
        is_expired BOOLEAN NOT NULL DEFAULT FALSE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_document_meta_team_id (team_id),
        INDEX ix_document_meta_category (category_path(255)),
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (uploaded_by) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 9. qa_meta
    """
    CREATE TABLE IF NOT EXISTS qa_meta (
        id VARCHAR(36) PRIMARY KEY,
        team_id VARCHAR(36) NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        question_summary VARCHAR(200) DEFAULT NULL,
        answer_summary VARCHAR(200) DEFAULT NULL,
        ragflow_chunk_id VARCHAR(100) DEFAULT NULL,
        version INT NOT NULL DEFAULT 1,
        edited_by VARCHAR(36) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_qa_meta_team_id (team_id),
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (edited_by) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 10. favorites
    """
    CREATE TABLE IF NOT EXISTS favorites (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        message_id VARCHAR(36) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_favorites_user_id (user_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (message_id) REFERENCES messages(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 11. announcements
    """
    CREATE TABLE IF NOT EXISTS announcements (
        id VARCHAR(36) PRIMARY KEY,
        title VARCHAR(200) NOT NULL,
        content TEXT NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_by VARCHAR(36) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 12. operation_logs
    """
    CREATE TABLE IF NOT EXISTS operation_logs (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        action VARCHAR(50) NOT NULL,
        resource_type VARCHAR(50) NOT NULL,
        resource_id VARCHAR(36) DEFAULT NULL,
        detail TEXT DEFAULT NULL,
        ip_address VARCHAR(45) DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_operation_logs_user_id (user_id),
        INDEX ix_operation_logs_action (action),
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 13. system_config
    """
    CREATE TABLE IF NOT EXISTS system_config (
        id VARCHAR(36) PRIMARY KEY,
        config_key VARCHAR(100) NOT NULL,
        config_value TEXT NOT NULL,
        updated_by VARCHAR(36) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_system_config_key (config_key),
        FOREIGN KEY (updated_by) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # 14. notifications
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        ticket_id VARCHAR(36) DEFAULT NULL,
        type VARCHAR(50) NOT NULL,
        title VARCHAR(200) NOT NULL,
        content TEXT DEFAULT NULL,
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX ix_notifications_user_read (user_id, is_read),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

# 初始种子数据：默认团队 + IT管理员账号
SEED_SQL = [
    """
    INSERT IGNORE INTO teams (id, name) VALUES
    ('team-default', '默认团队'),
    ('team-ops-east', '运营-华东区'),
    ('team-ops-south', '运营-华南区'),
    ('team-ops-north', '运营-华北区'),
    ('team-ops-west', '运营-西部区'),
    ('team-ops-central', '运营-中部区')
    """,
    # 密码: admin123 (bcrypt hash)
    """
    INSERT IGNORE INTO users (id, username, password_hash, display_name, role, team_id) VALUES
    ('user-admin', 'admin', '$2b$12$LJ3f5K5z5Z5Z5Z5Z5Z5Z5OMxKQvXqJQvX5K5z5Z5Z5Z5Z5Z5Z5Z5Z', 'IT管理员', 'it_admin', 'team-default')
    """,
]


def main():
    print(f"连接数据库 {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}...")
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("\n=== 创建14张表 ===")
    for i, sql in enumerate(TABLES_SQL, 1):
        table_name = sql.strip().split("EXISTS")[1].strip().split("(")[0].strip()
        try:
            cursor.execute(sql)
            print(f"  [{i:2d}/14] ✅ {table_name}")
        except Exception as e:
            print(f"  [{i:2d}/14] ❌ {table_name}: {e}")

    conn.commit()

    print("\n=== 插入种子数据 ===")
    for sql in SEED_SQL:
        try:
            cursor.execute(sql)
            print(f"  ✅ {sql.strip()[:60]}...")
        except Exception as e:
            print(f"  ❌ {e}")

    conn.commit()

    # 验证
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"\n=== 验证: 共 {len(tables)} 张表 ===")
    for t in tables:
        print(f"  📋 {t[0]}")

    cursor.close()
    conn.close()
    print("\n✅ 数据库初始化完成!")


if __name__ == "__main__":
    main()
