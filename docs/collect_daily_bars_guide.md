# 日线行情数据采集使用指南

## 概述

`collect_daily_bars.py` 是专业的量化交易日线行情采集脚本，支持：

- ✅ **优先级采集**：P0核心标的池（~60个）、P1扩展池、P2研究池
- ✅ **主题驱动**：按13个核心主题组织标的
- ✅ **严格限速**：0.6秒基础间隔 + 批次冷却，避免触发Tushare限制
- ✅ **断点续采**：增量模式自动从最后日期继续
- ✅ **数据质量**：OHLC一致性检查、重复检测
- ✅ **重试机制**：指数退避 + 冷却期检测
- ✅ **演练模式**：dry-run测试不写入数据库

## 快速开始

### 1. P0核心标的池采集（推荐）

```bash
# 增量采集（从最后日期继续）
uv run python scripts/collect_daily_bars.py --priority P0 --incremental

# 全量采集（最近3年）
uv run python scripts/collect_daily_bars.py --priority P0 --start 20210101 --end 20241231

# 演练模式（不写入数据库）
uv run python scripts/collect_daily_bars.py --priority P0 --incremental --dry-run
```

### 2. 单个标的采集

```bash
# 采集沪深300ETF最近一个月数据
uv run python scripts/collect_daily_bars.py \
  --symbol 510300.SH \
  --asset-type ETF \
  --start 20240501 \
  --end 20240531

# 增量采集单个标的
uv run python scripts/collect_daily_bars.py \
  --symbol 510300.SH \
  --asset-type ETF \
  --incremental
```

### 3. 按主题采集（待实现）

```bash
# 采集科技主题相关标的
uv run python scripts/collect_daily_bars.py --theme tech --incremental
```

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--priority` | 优先级：P0/P1/P2 | `--priority P0` |
| `--theme` | 主题ID（待实现） | `--theme tech` |
| `--symbol` | 单个证券代码 | `--symbol 510300.SH` |
| `--asset-type` | 资产类型：ETF/INDEX/STOCK | `--asset-type ETF` |
| `--start` | 开始日期 YYYYMMDD | `--start 20240101` |
| `--end` | 结束日期 YYYYMMDD | `--end 20241231` |
| `--incremental` | 增量模式（从最后日期继续） | `--incremental` |
| `--dry-run` | 演练模式（不写入数据库） | `--dry-run` |

## 配置文件

### P0核心标的池 (`configs/universe/p0_core.yaml`)

包含62个核心标的：
- 14个基准指数（沪深300、上证指数、中证科技龙头等）
- 48个代表ETF（每个主题2-3个）
- 覆盖13个核心主题

### 主题配置 (`configs/themes/theme_universe.yaml`)

13个核心主题：
1. 科技（tech）
2. 消费（consumer）
3. 医药（healthcare）
4. 新能源（new_energy）
5. 金融（finance）
6. 地产基建（realestate）
7. 军工（defense）
8. 周期（cyclical）
9. 红利（dividend）
10. 成长（growth）
11. 央企（soe）
12. 港股（hkstock）
13. 宽基（broad）

### 限速配置 (`configs/data_sources/rate_limit.yaml`)

```yaml
tushare:
  base_interval: 0.6          # 每次请求间隔0.6秒
  batch_limits:
    - requests: 50            # 50次后冷却60秒
      cooldown: 60
    - requests: 200           # 200次后冷却300秒
      cooldown: 300
  retry:
    max_attempts: 3           # 最大重试3次
    initial_backoff: 2.0      # 初始退避2秒
    exponential_base: 2.0     # 指数退避
```

## 核心功能

### 1. 严格限速

脚本**真实执行**限速，不是注释：

```python
# 基础限速：每次请求间隔至少0.6秒
wait_time = self.rate_limiter.wait()

# 批次限速：50次后冷却60秒，200次后冷却300秒
# 自动检测并执行冷却
```

日志中可以看到实际等待时间：
```
限速等待: 0.600秒
批次限速触发: 已连续请求50次，冷却60秒
```

### 2. 断点续采

增量模式自动查询数据库中的最后日期：

```python
# 查询最后交易日期
checkpoint = self.get_checkpoint_date(symbol, asset_type)

# 从下一天开始采集
if checkpoint:
    next_date = checkpoint + 1天
    logger.info(f"增量模式: 从 {next_date} 开始")
```

### 3. 数据质量检查

自动检查OHLC一致性：
- high >= low
- high >= open, close
- low <= open, close
- 价格 > 0
- 重复数据检测

### 4. 重试机制

- 指数退避：2秒 → 4秒 → 8秒
- 冷却期检测：识别"频率"、"冷却"等关键词
- 自动等待360秒后重试

## 数据验证

### 查询采集的数据

```sql
-- 查看510300.SH的数据
SELECT symbol, trade_date, open, high, low, close, vol
FROM daily_bars
WHERE symbol = '510300.SH'
ORDER BY trade_date DESC
LIMIT 10;

-- 统计各标的的数据量
SELECT symbol, asset_type, count(*) as bars_count
FROM daily_bars
GROUP BY symbol, asset_type
ORDER BY bars_count DESC;

-- 查看最近采集的数据
SELECT symbol, asset_type, max(trade_date) as latest_date, count(*) as bars
FROM daily_bars
GROUP BY symbol, asset_type
ORDER BY latest_date DESC;
```

### 查看采集状态

```sql
-- 查看数据源状态
SELECT source_name, data_type, status, rows_processed, last_success_time
FROM source_status
ORDER BY last_success_time DESC;

-- 查看任务运行日志
SELECT job_name, status, rows_written, start_time, end_time
FROM job_run_log
ORDER BY start_time DESC
LIMIT 10;
```

## 性能指标

### P0核心标的池（62个标的）

| 指标 | 预估值 |
|------|--------|
| 标的数量 | 62个 |
| 每个标的数据量 | ~1000条（3年） |
| 总数据量 | ~62,000条 |
| 总请求次数 | 62次 |
| 基础限速时间 | 62 × 0.6 = 37秒 |
| 批次冷却时间 | 60秒（50次后） |
| **预计总耗时** | **~2-3分钟** |

### 增量采集（每日）

| 指标 | 预估值 |
|------|--------|
| 标的数量 | 62个 |
| 每个标的新增 | 1条 |
| 总请求次数 | 62次 |
| **预计总耗时** | **~1-2分钟** |

## 最佳实践

### 1. 首次采集

```bash
# 1. 先演练测试
uv run python scripts/collect_daily_bars.py --priority P0 --start 20210101 --dry-run

# 2. 确认无误后正式采集
uv run python scripts/collect_daily_bars.py --priority P0 --start 20210101
```

### 2. 每日更新

```bash
# 增量采集（自动从最后日期继续）
uv run python scripts/collect_daily_bars.py --priority P0 --incremental
```

### 3. 补充缺失数据

```bash
# 指定日期区间补充
uv run python scripts/collect_daily_bars.py --priority P0 --start 20240101 --end 20240131
```

### 4. 单个标的测试

```bash
# 先用单个标的测试
uv run python scripts/collect_daily_bars.py \
  --symbol 510300.SH \
  --asset-type ETF \
  --start 20240501 \
  --end 20240510 \
  --dry-run
```

## 日志说明

### 正常日志

```
2026-06-01 10:47:34 | INFO | 限速器初始化: base_interval=0.6s
2026-06-01 10:47:34 | INFO | 批次限制: 50次请求后冷却60秒
2026-06-01 10:47:35 | INFO | 采集: 510300.SH (ETF, broad)
2026-06-01 10:47:35 | INFO | 请求: 20240501 ~ 20240510
2026-06-01 10:47:36 | INFO | 获取: 5 条
2026-06-01 10:47:36 | INFO | ✓ 写入: 5 条
```

### 限速日志

```
2026-06-01 10:48:00 | DEBUG | 基础限速: 等待 0.600s
2026-06-01 10:50:00 | WARNING | 批次限速触发: 已连续请求50次，冷却60秒
```

### 重试日志

```
2026-06-01 10:48:30 | WARNING | 请求失败 (尝试 1/3): 网络错误
2026-06-01 10:48:30 | INFO | 等待 2.0 秒后重试...
2026-06-01 10:48:32 | INFO | ✓ 重试成功 (尝试 2/3)
```

### 冷却期日志

```
2026-06-01 10:49:00 | WARNING | 检测到冷却期错误: 抱歉，您的访问频率过高
2026-06-01 10:49:00 | WARNING | 等待 360 秒后重试...
```

## 故障排查

### 1. 连接失败

```bash
# 检查ClickHouse是否运行
docker ps | grep clickhouse

# 检查网络连接
docker exec fund_quant_clickhouse clickhouse-client --query "SELECT 1"
```

### 2. Tushare限速

如果频繁触发限速，调整配置：

```yaml
# configs/data_sources/rate_limit.yaml
tushare:
  base_interval: 1.0  # 增加到1秒
```

### 3. 数据质量问题

查看质量检查日志：
```
数据质量问题: high < low: 2条, 价格<=0: 1条
```

手动检查问题数据：
```sql
SELECT * FROM daily_bars
WHERE symbol = '510300.SH' AND (high < low OR close <= 0);
```

## 下一步

- [ ] 实现P1扩展标的池配置
- [ ] 实现按主题采集功能
- [ ] 添加采集进度条
- [ ] 实现并发采集（多线程）
- [ ] 添加数据质量评分
- [ ] 实现自动补全缺失交易日

## 相关文档

- [Phase 2 完成总结](../docs/phase2_symbols_collection_summary.md)
- [ClickHouse表结构](../sql/clickhouse/)
- [配置文件说明](../configs/)
