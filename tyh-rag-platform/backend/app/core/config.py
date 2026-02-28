"""应用配置管理 - 支持环境变量 + Nacos"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """系统配置 - 优先从环境变量读取，生产环境从Nacos获取"""

    # ========== 基础配置 ==========
    APP_NAME: str = "AI知识库系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ========== 数据库配置 ==========
    DATABASE_URL: str = "mysql+aiomysql://skyline-test:Vi689PdhZTHMIcTuN8A@172.31.1.3:4000/knowledge_base?charset=utf8mb4"

    # ========== Redis配置 ==========
    REDIS_URL: str = "redis://localhost:6379/0"

    # ========== JWT配置 ==========
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8小时

    # ========== RAGflow配置 ==========
    # RAGFlow 连接配置（全局唯一，所有团队共用同一个 RAGFlow 实例）
    # 助手ID和知识库ID已迁移到 team_configs / team_datasets 表，由IT管理员按团队配置
    RAGFLOW_BASE_URL: str = "http://127.0.0.1/api/v1"
    RAGFLOW_API_KEY: str = "ragflow-kvz3G-Vb9TdEJdcrVdV5kzAGLuI0YC1GCLCOGKaN1nQ"

    # ========== DeepSeek配置 ==========
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # ========== OBS配置 ==========
    OBS_ENDPOINT: str = ""
    OBS_ACCESS_KEY: str = ""
    OBS_SECRET_KEY: str = ""
    OBS_BUCKET: str = ""

    # ========== CORS配置 ==========
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ========== Nacos配置 ==========
    NACOS_SERVER: str = ""
    NACOS_NAMESPACE: str = ""
    NACOS_DATA_ID: str = "knowledge-base"
    NACOS_GROUP: str = "DEFAULT_GROUP"

    # ========== 内容过滤 ==========
    CONTENT_FILTER_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
