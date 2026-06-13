# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

机构级量化交易系统 - 基于新闻事件驱动的主题/ETF轮动策略系统。系统采集多源财经新闻，通过NLP处理提取事件，映射到主题/行业/个股/ETF，计算因子，生成信号，构建组合并执行交易。

**架构流程**: 新闻采集 → NLP处理 → 事件抽取 → 主题映射 → 因子计算 → 信号生成 → 组合构建 → 风控 → 执行

## 技术栈

- **数据存储**: ClickHouse (时序数据), Redis (缓存), Parquet (特征)
- **计算框架**: Pandas, Polars, NumPy
- **NLP**: Transformers, LLM API (OpenAI, Anthropic)
- **数据源**: Tushare, AKShare, 财联社, Reuters, Reddit, X
- **容器化**: Docker Compose (ClickHouse + Redis)

## 包管理器

本项目使用 **uv** (不是 pip 或 poetry)。所有 Python 命令都应使用:
```bash
uv run python <script>
```

## 环境配置

1. 复制环境变量模板:
```bash
cp .env.example .env
```

2. 在 `.env` 中配置必需的环境变量:
- `TUSHARE_TOKEN`: 主要数据源API令牌 (从 https://tushare.pro/ 获取)
- `TUSHARE_API_URL`: 自定义API地址 (默认: https://tt.xiaodefa.cn)
- `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`: 数据库连接
- `REDIS_HOST`, `REDIS_PORT`: 缓存连接
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`: NLP所需的LLM API

3. 启动基础设施:
```bash
make up  # 启动 ClickHouse + Redis 容器
```

4. 初始化数据库表结构:
```bash
uv run python scripts/init_clickhouse.py
```

## 常用命令

### 开发相关
```bash
make install          # 安装依赖 (pip install -e .)
make dev             # 安装开发依赖 (pytest, black, ruff, mypy)
make up              # 启动 ClickHouse + Redis 容器
make down            # 停止容器
make clean           # 清理 Python 缓存文件
```

### 代码质量
```bash
make format          # 格式化代码 (black + ruff fix)
make lint            # 代码检查 (ruff + mypy)
make test            # 运行测试 (pytest with coverage)
```

### 数据采集

**日线行情采集** (主要脚本):
```bash
# 测试单个标的（演练模式，不写入数据库）
uv run python scripts/collect_daily_bars.py \
  --symbol 510300.SH --asset-type ETF \
  --start 20240501 --end 20240510 --dry-run

# 采集P0核心标的池（62个标的）
uv run python scripts/collect_daily_bars.py \
  --priority P0 --start 20240101 --end 20241231

# 增量更新（自动检测最后日期）
uv run python scripts/collect_daily_bars.py \
  --priority P0 --incremental
```

**新闻采集**:
```bash
uv run python scripts/collect_news.py --source all
uv run python scripts/collect_cls_to_db.py  # 财联社专用
```

**主题数据**:
```bash
uv run python scripts/collect_theme_index_data.py
uv run python scripts/calculate_theme_factors.py
```

### 数据库操作

**查询数据** (通过 ClickHouse CLI):
```bash
# 查看行情数据
docker exec fund_quant_clickhouse clickhouse-client --database quant --query \
  "SELECT symbol, trade_date, close, volume FROM daily_bars WHERE symbol='510300.SH' ORDER BY trade_date DESC LIMIT 10"

# 检查采集状态
docker exec fund_quant_clickhouse clickhouse-client --database quant --query \
  "SELECT source_name, data_type, status, rows_processed, last_success_time FROM source_status ORDER BY last_success_time DESC"

# 查看任务日志
docker exec fund_quant_clickhouse clickhouse-client --database quant --query \
  "SELECT job_name, status, rows_written, start_time, end_time FROM job_run_log ORDER BY start_time DESC LIMIT 10"
```

### 回测
```bash
uv run python scripts/run_backtest.py \
  --strategy theme_rotation \
  --start 20240101 --end 20241231
```

## 代码架构

### 模块结构

```
src/fund_quant/
├── common/          # 配置、日志、枚举
├── data/            # 数据获取、规范化、质量检查、存储、模式定义
├── data_sources/    # Tushare、AKShare 适配器
├── market/          # 行情、日线、基本面、指数、ETF、交易日历
├── nlp/             # 文本清洗、分类、事件抽取、情绪分析、实体链接
├── knowledge/       # 主题、行业、个股、ETF、供应链映射
├── features/        # 新闻、市场、流动性、技术特征
├── factors/         # 新闻Alpha、动量、量价、情绪、流动性因子
├── strategy/        # theme_rotation、etf_rotation、event_driven、stock_selection
├── portfolio/       # 组合构建
├── risk/            # 风险管理
├── execution/       # 订单执行
├── backtest/        # 回测框架
├── monitoring/      # 系统监控
├── api/             # REST API
├── pipelines/       # 端到端工作流
└── research/        # 研究笔记本、实验
```

### 核心数据流

1. **数据层** (`data/`, `data_sources/`, `market/`):
   - `data/ingestion`: 从外部API获取数据
   - `data/storage`: ClickHouse客户端、模式管理
   - `market/bars`: 带限速的日线行情服务
   
2. **NLP管线** (`nlp/`, `knowledge/`):
   - 新闻 → 事件抽取 → 主题/个股映射
   - 知识图谱: 主题 ↔ 行业 ↔ 个股 ↔ ETF

3. **因子计算** (`features/`, `factors/`):
   - 原始特征 → 标准化因子 → 信号生成

4. **策略执行** (`strategy/`, `portfolio/`, `risk/`, `execution/`):
   - 信号 → 组合构建 → 风控检查 → 订单执行

### 重要实现细节

**限速机制**: 系统严格执行限速以遵守Tushare API配额:
- 每次请求间隔 0.6秒
- 50次请求后冷却 60秒
- 200次请求后冷却 300秒
- 配置文件: `configs/data_sources/rate_limit.yaml`

**增量采集**: 脚本会查询 `daily_bars` 表中每个标的的最后交易日期，只获取新数据。使用 `--incremental` 标志启用。

**数据质量**: 所有数据获取都包含验证:
- OHLC一致性检查 (high ≥ close ≥ low 等)
- 重复数据检测
- 通过 `data/schemas` 进行模式验证

**ClickHouse表结构**: 表定义在 `sql/clickhouse/`，通过 `scripts/init_clickhouse.py` 初始化:
- `symbol_master`: 标的元数据
- `daily_bars`: OHLC数据
- `raw_news`: 未处理的新闻
- `extracted_events`: NLP处理结果
- `source_status`, `job_run_log`: 监控表

**配置文件**: 核心配置在 `configs/`:
- `universe/p0_core.yaml`: 优先级标的列表（62个核心ETF/指数）
- `themes/`: 主题库、主题-ETF映射
- `market/market_indices.yaml`: 宽基指数
- `data_sources/rate_limit.yaml`: API限速设置

### 测试流程

在全量采集前建议的测试步骤:
1. 使用 `--dry-run` 标志测试单个标的
2. 验证单个标的的数据库写入
3. 测试增量模式
4. 在P0标的池运行（62个标的）
5. 设置cron任务进行每日增量更新

## 开发工作流

1. 启动基础设施: `make up`
2. 验证容器: `docker ps` (应看到 `fund_quant_clickhouse`, `fund_quant_redis`)
3. 首次运行需初始化数据库: `uv run python scripts/init_clickhouse.py`
4. 使用 `--dry-run` 测试数据采集
5. 运行实际采集
6. 在ClickHouse中验证数据
7. 提交前格式化代码: `make format`

## 重要约束

- 运行脚本必须使用 `uv run python`
- 所有市场数据操作都需要Tushare token
- 限速在运行时强制执行 - 采集过程中会有真实的等待延迟
- ClickHouse提供原生端口(9000)和HTTP端口(8123)
- 时区: Asia/Shanghai (A股市场交易时段)
- 数据库名: `quant` (大多数查询中硬编码)

## 文档

- `README.md`: 系统高层概述
- `QUICKSTART.md`: 逐步采集工作流程
- `docs/tushare_setup.md`: Tushare API配置和使用
- `configs/` 中的配置文件: 带示例的自文档化YAML
