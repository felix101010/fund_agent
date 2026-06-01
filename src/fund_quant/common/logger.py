"""日志模块"""
import sys
from loguru import logger
from pathlib import Path

from .config import settings


def setup_logger():
    """配置日志"""
    # 移除默认handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 文件输出
    log_file = settings.log_dir / "quant_{time:YYYY-MM-DD}.log"
    logger.add(
        log_file,
        rotation="00:00",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    return logger


log = setup_logger()
