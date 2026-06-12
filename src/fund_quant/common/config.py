"""配置管理模块"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """系统配置"""

    # 数据源
    tushare_token: str = ""
    tushare_api_url: str = ""
    akshare_proxy: str = ""

    # 数据库
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_db: str = "quant"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    # API
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Ollama
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:1.5b"

    # 系统
    log_level: str = "INFO"
    env: str = "dev"
    tz: str = "Asia/Shanghai"

    # 路径
    base_dir: Path = Path(__file__).parent.parent.parent.parent
    data_dir: Path = base_dir / "data"
    log_dir: Path = base_dir / "logs"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
