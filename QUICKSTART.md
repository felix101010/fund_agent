# 快速开始指南

## 1. 测试单个标的（推荐先测试）

```bash
# 测试采集沪深300ETF最近10天数据（演练模式，不写入数据库）
uv run python scripts/collect_daily_bars.py \
  --symbol 510300.SH \
  --asset-type ETF \
  --start 20240501 \
  --end 20240510 \
  --dry-run

# 实际写入数据库
uv run python scripts/collect_daily_bars.py \
  --symbol 510300.SH \
  --asset-type ETF \
  --start 20240501 \
  --end 20240510
```

## 2. 验证数据

```bash
# 查看写入的数据
docker exec fund_quant_clickhouse clickhouse-client --database quant --query \
  "SELECT symbol, trade_date, open, high, low, close, volume 
   FROM daily_bars 
   WHERE symbol='510300.SH' 
   ORDER BY trade_date"

# 统计数据量
docker exec fund_quant_clickhouse clickhouse-client --database quant --query \
  "SELECT symbol, asset_type, count(*) as bars_count 
   FROM daily_bars 
   GROUP BY symbol, asset_type"
```

## 3. 测试增量采集

```bash
# 第一次：采集5月1-10日
uv run python scripts/collect_daily_bars.py \
  --symbol 510300.SH \
  --asset-type ETF \
  --start 20240501 \
  --end 20240510

# 第二次：增量采集（会自动从5月11日开始）
uv run python scripts/collect_daily_bars.py \
  --symbol 510300.SH \
  --asset-type ETF \
  --start 20240501 \
  --end 20240520 \
  --incremental
```

## 4. 采集P0核心标的池（62个标的）

```bash
# 演练模式（先测试，不写入）
uv run python scripts/collect_daily_bars.py \
  --priority P0 \
  --start 20240101 \
  --end 20240531 \
  --dry-run

# 正式采集（约2-3分钟，62个标的 × 0.6秒限速）
uv run python scripts/collect_daily_bars.py \
  --priority P0 \
  --start 20240101 \
  --end 20240531
```

## 5. 每日增量更新

```bash
# 每天运行一次，自动从最后日期继续
uv run python scripts/collect_daily_bars.py \
  --priority P0 \
  --incremental
```

## 6. 查看P0标的池配置

```bash
# 查看包含哪些标的
cat configs/universe/p0_core.yaml

# 查看主题配置
cat configs/themes/theme_universe.yaml

# 查看限速配置
cat configs/data_sources/rate_limit.yaml
```

## 7. 监控采集状态

```bash
# 查看数据源状态
docker exec fund_quant_clickhouse clickhouse-client --database quant --query \
  "SELECT source_name, data_type, status, rows_processed, last_success_time 
   FROM source_status 
   ORDER BY last_success_time DESC"

# 查看任务运行日志
docker exec fund_quant_clickhouse clickhouse-client --database quant --query \
  "SELECT job_name, status, rows_written, start_time, end_time 
   FROM job_run_log 
   ORDER BY start_time DESC 
   LIMIT 10"
```

## 常见场景

### 场景1：首次采集历史数据（3年）

```bash
# 采集2021-2024年数据
uv run python scripts/collect_daily_bars.py \
  --priority P0 \
  --start 20210101 \
  --end 20241231
```

预计耗时：
- 62个标的 × 0.6秒基础限速 = 37秒
- 50次后冷却60秒 = 60秒
- 总计约 **2-3分钟**

### 场景2：每日定时更新

```bash
# 添加到crontab，每天收盘后运行
# 0 16 * * 1-5 cd /path/to/project && uv run python scripts/collect_daily_bars.py --priority P0 --incremental

# 手动运行
uv run python scripts/collect_daily_bars.py --priority P0 --incremental
```

### 场景3：补充缺失数据

```bash
# 补充某个时间段的数据
uv run python scripts/collect_daily_bars.py \
  --priority P0 \
  --start 20240301 \
  --end 20240331
```

### 场景4：测试新标的

```bash
# 测试科创50ETF
uv run python scripts/collect_daily_bars.py \
  --symbol 515000.SH \
  --asset-type ETF \
  --start 20240101 \
  --end 20240531 \
  --dry-run
```

## 重要提示

1. **限速严格执行**：脚本会真实等待0.6秒，50次后冷却60秒，200次后冷却300秒
2. **增量模式智能**：自动查询最后日期，只采集新数据
3. **演练模式安全**：`--dry-run` 不写入数据库，可以放心测试
4. **数据质量检查**：自动检查OHLC一致性和重复数据

## 下一步

查看完整文档：
```bash
cat docs/collect_daily_bars_guide.md
```
