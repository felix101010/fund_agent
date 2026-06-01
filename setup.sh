#!/bin/bash
# 机构级量化系统目录结构初始化脚本

set -e

BASE_DIR=~/workspace/funding/agent/fund_quant_system
cd "$BASE_DIR"

echo "创建目录结构..."

# 配置目录
mkdir -p configs/{dev,prod,sources,strategies,risk,logging}

# 源代码目录
mkdir -p src/fund_quant/{common,data,nlp,knowledge,market,features,factors,research,strategy,portfolio,risk,backtest,execution,pipelines,monitoring,api}

# 数据子模块
mkdir -p src/fund_quant/data/{ingestion,normalization,quality,storage,schemas,lineage}

# NLP子模块
mkdir -p src/fund_quant/nlp/{cleaning,classification,event_extraction,sentiment,entity_linking,prompts}

# 知识库子模块
mkdir -p src/fund_quant/knowledge/{themes,industries,stocks,etfs,supply_chain}

# 行情子模块
mkdir -p src/fund_quant/market/{quotes,bars,fundamentals,index,etf,calendar}

# 特征工程子模块
mkdir -p src/fund_quant/features/{news_features,market_features,liquidity_features,technical_features}

# 因子研究子模块
mkdir -p src/fund_quant/factors/{news_alpha,momentum,volume_price,sentiment,liquidity}

# 研究子模块
mkdir -p src/fund_quant/research/{notebooks,experiments,factor_tests,reports}

# 策略子模块
mkdir -p src/fund_quant/strategy/{theme_rotation,etf_rotation,event_driven,stock_selection}

# 脚本目录
mkdir -p scripts

# SQL目录
mkdir -p sql/{clickhouse,migrations,views}

# 数据目录
mkdir -p data/{raw,normalized,features,factors,backtest}

# Notebooks目录
mkdir -p notebooks/{factor_research,news_analysis,strategy_test}

# 测试目录
mkdir -p tests/{unit,integration,data_quality,backtest_regression}

# 文档目录
mkdir -p docs

# 其他目录
mkdir -p {logs,reports,tmp}

echo "创建 __init__.py 文件..."

# 创建所有Python包的__init__.py
find src -type d -exec touch {}/__init__.py \;

echo "创建配置文件..."

# .env.example
cat > .env.example << 'EOF'
# 数据源配置
TUSHARE_TOKEN=your_token_here
AKSHARE_PROXY=

# 数据库配置
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DB=quant

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# API配置
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# 系统配置
LOG_LEVEL=INFO
ENV=dev
TZ=Asia/Shanghai
EOF

# docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: quant_clickhouse
    ports:
      - "9000:9000"
      - "8123:8123"
    volumes:
      - ./data/clickhouse:/var/lib/clickhouse
      - ./sql/clickhouse:/docker-entrypoint-initdb.d
    environment:
      CLICKHOUSE_DB: quant
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: quant_redis
    ports:
      - "6379:6379"
    volumes:
      - ./data/redis:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: quant_grafana
    ports:
      - "3000:3000"
    volumes:
      - ./data/grafana:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    restart: unless-stopped
EOF

# Makefile
cat > Makefile << 'EOF'
.PHONY: help install dev up down clean test lint format

help:
	@echo "Fund Quant System - Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make install    - 安装依赖"
	@echo "  make dev        - 安装开发依赖"
	@echo "  make up         - 启动服务"
	@echo "  make down       - 停止服务"
	@echo "  make clean      - 清理临时文件"
	@echo "  make test       - 运行测试"
	@echo "  make lint       - 代码检查"
	@echo "  make format     - 代码格式化"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

up:
	docker-compose up -d

down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf build dist *.egg-info

test:
	pytest tests/ -v --cov=src/fund_quant

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/ scripts/
	ruff check --fix src/ tests/
EOF

echo "创建核心模块文件..."

# common/config.py
cat > src/fund_quant/common/config.py << 'EOF'
"""配置管理模块"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """系统配置"""

    # 数据源
    tushare_token: str = ""
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
EOF

# common/logger.py
cat > src/fund_quant/common/logger.py << 'EOF'
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
EOF

# common/enums.py
cat > src/fund_quant/common/enums.py << 'EOF'
"""枚举类型定义"""
from enum import Enum


class DataSource(str, Enum):
    """数据源"""
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    CAILIAN = "cailian"
    JUCHAO = "juchao"
    REUTERS = "reuters"
    REDDIT = "reddit"
    TWITTER = "twitter"


class AssetType(str, Enum):
    """资产类型"""
    STOCK = "stock"
    ETF = "etf"
    INDEX = "index"
    FUND = "fund"


class EventType(str, Enum):
    """事件类型"""
    PRODUCT_RELEASE = "product_release"
    EARNINGS = "earnings"
    REGULATION = "regulation"
    MERGER = "merger"
    INVESTMENT = "investment"
    MACRO = "macro"
    GEOPOLITICS = "geopolitics"


class Sentiment(str, Enum):
    """情绪"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SignalType(str, Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
EOF

echo "✓ 目录结构创建完成！"
echo ""
echo "下一步："
echo "1. cd $BASE_DIR"
echo "2. cp .env.example .env"
echo "3. 编辑 .env 填入配置"
echo "4. make install"
echo "5. make up"
