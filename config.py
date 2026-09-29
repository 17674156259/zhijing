"""
配置管理
========
集中管理所有配置项，从 .env 文件或环境变量读取。
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """应用配置"""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # 数据库
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "diagnosis.db"
    ))

    # LLM 配置
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock").strip().lower()
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
    LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-plus").strip()
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").strip()

    # Flask-CORS
    CORS_ORIGINS = "*"
