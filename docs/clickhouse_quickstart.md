# ClickHouse 数据底座快速开始

## 📋 已完成的工作

### 1. ClickHouse 表结构（P0核心表）

已创建 6 个核心表：

- ✅ `symbol_master` - 证券主数据表（ETF/股票/指数）
- ✅ `daily_bars` - 统一日线行情表
- ✅ `source_status` - 数据源状态追踪表
- ✅ `job_run_log` - 任务运行日志表
- ✅ `raw_news` - 原始新闻表
- ✅ `extracted_events` - 新闻事件抽取结果表

### 2. 数据访问层

- ✅ `ClickHouseClient` - 统一的数据库操作接口
  - 连接管理
  - 批量写入 `insert_many()`
  - 查询封装 `query_df()`
  - 状态更新 `update_source_status()`
  - 日志记录 `write_job_run_log()`

### 3. 初始化脚本

- ✅ `scripts/init_clickhouse.py` - 自动创建所有表

---

## 🚀 快速启动

### Step 1: 启动 ClickHouse

```bash
cd /home/felix/workspace/funding/agent/fund_quant_system

# 启动 Docker 容器
docker-compose up -d clickhouse

# 查看日志
docker-compose logs -f clickhouse

# 等待 ClickHouse 启动完成（约10-20秒）
```

### Step 2: 初始化数据库表

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装 clickhouse-driver（如果还没安装）
uv pip install clickhouse-driver

# 执行初始化脚本
python scripts/init_clickhouse.py
```

**预期输出**：
```
============================================================
开始初始化 ClickHouse 数据库
============================================================

执行: 001_symbol_master.sql
✓ 001_symbol_master.sql 执行成功

执行: 002_daily_bars.sql
✓ 002_daily_bars.sql 执行成功

...

已创建的表 (6 个):
  - symbol_master
  - daily_bars
  - source_status
  - job_run_log
  - raw_news
  - extracted_events

✓ 所有表创建成功！
```

### Step 3: 验证安装

```bash
# 方式1: 使用 clickhouse-client（如果已安装）
clickhouse-client --host localhost --port 9000

# 在 ClickHouse 客户端中执行
USE quant;
SHOW TABLES;
DESC symbol_master;

# 方式2: 使用 Python 测试
python -c "
from fund_quant.data.storage import ClickHouseClient
client = ClickHouseClient()
tables = client.query_df('SHOW TABLES')
print(tables)
"
```

---

## 📊 表结构说明

### 1. symbol_master（证券主数据）

存储 ETF、股票、指数的基础信息。

**关键字段**：
- `symbol` - 证券代码（如 159272.SZ）
- `name` - 证券名称
- `asset_type` - 资产类型（ETF/STOCK/INDEX）
- `status` - 状态（active/delisted/suspended）

### 2. daily_bars（日线行情）

统一存储所有资产的日线数据。

**关键字段**：
- `symbol`, `asset_type`, `trade_date` - 主键
- `open`, `high`, `low`, `close` - OHLC
- `volume`, `amount` - 成交量、成交额
- `adj_factor` - 复权因子（股票用）

**重要**：按 `(symbol, asset_type, trade_date)` 排序，支持高效的时间序列查询。

### 3. source_status（数据源状态）

追踪每个数据源的最新采集状态。

**用途**：
- 知道每个数据源最新跑到哪里了
- 支持增量更新
- 支持断点续跑

### 4. job_run_log（任务日志）

记录每次数据采集任务的执行情况。

**用途**：
- 任务成功/失败追踪
- 性能监控
- 问题排查

### 5. raw_news（原始新闻）

存储从各渠道采集的原始新闻。

**关键设计**：
- `published_at` - 新闻发布时间
- `collected_at` - 系统采集时间（**回测用此时间**）
- `url_hash`, `content_hash`, `dedup_key` - 三重去重

### 6. extracted_events（事件抽取）

存储从新闻中提取的结构化事件。

**关键设计**：
- `model_name` + `prompt_version` - 保证可复现
- `a_share_mapping` - 是否有A股映射
- `related_etfs` - 相关ETF代码

---

## 🔧 常用操作

### 查询示例

```sql
-- 查询所有活跃的ETF
SELECT symbol, name, list_date 
FROM symbol_master 
WHERE asset_type = 'ETF' AND status = 'active' 
ORDER BY list_date DESC;

-- 查询某个ETF的最近行情
SELECT trade_date, close, pct_chg, amount 
FROM daily_bars 
WHERE symbol = '159272.SZ' AND asset_type = 'ETF' 
ORDER BY trade_date DESC 
LIMIT 30;

-- 查询数据源状态
SELECT source_name, data_type, last_success_time, status 
FROM source_status 
ORDER BY last_success_time DESC;

-- 查询最近的任务执行情况
SELECT job_name, start_time, status, rows_written 
FROM job_run_log 
ORDER BY start_time DESC 
LIMIT 20;
```

### Python 操作示例

```python
from fund_quant.data.storage import ClickHouseClient

# 初始化客户端
client = ClickHouseClient()

# 查询数据
df = client.query_df("""
    SELECT symbol, name 
    FROM symbol_master 
    WHERE asset_type = 'ETF' 
    LIMIT 10
""")
print(df)

# 批量插入
rows = [
    {
        'symbol': '159272.SZ',
        'name': '华夏科创50ETF',
        'asset_type': 'ETF',
        'exchange': 'SZ',
        'list_date': '2020-09-22',
        'status': 'active',
        'source': 'tushare'
    }
]
client.insert_many('symbol_master', rows)

# 更新数据源状态
client.update_source_status(
    source_name='tushare_etf',
    data_type='symbols',
    status='success',
    rows_processed=100
)

# 写入任务日志
from datetime import datetime
client.write_job_run_log(
    job_name='collect_etf_symbols',
    source_name='tushare',
    start_time=datetime.now(),
    status='success',
    rows_written=100
)
```

---

## 📝 下一步

现在数据库基础已经搭建完成，接下来可以：

1. **实现证券主数据采集** - `scripts/collect_symbols.py`
   - 采集所有 ETF 列表
   - 采集指数列表
   - 写入 `symbol_master` 表

2. **实现日线行情采集** - `scripts/collect_daily_bars.py`
   - 支持增量更新
   - 支持区间回补
   - 写入 `daily_bars` 表

3. **数据质量检查** - `scripts/run_data_quality_check.py`
   - 检查数据完整性
   - 检查异常值

---

## 🐛 故障排查

### ClickHouse 连接失败

```bash
# 检查容器状态
docker-compose ps

# 查看日志
docker-compose logs clickhouse

# 重启容器
docker-compose restart clickhouse
```

### 表创建失败

```bash
# 删除所有表重新创建
clickhouse-client --host localhost --port 9000 --query "DROP DATABASE IF EXISTS quant"
python scripts/init_clickhouse.py
```

### 权限问题

```bash
# 确保数据目录有写权限
sudo chown -R $USER:$USER data/clickhouse
```

---

## 📚 参考资料

- [ClickHouse 官方文档](https://clickhouse.com/docs)
- [clickhouse-driver 文档](https://clickhouse-driver.readthedocs.io/)
- 表结构定义：`sql/clickhouse/*.sql`
- 数据访问层：`src/fund_quant/data/storage/clickhouse_client.py`
