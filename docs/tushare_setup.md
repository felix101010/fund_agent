# Tushare 配置说明

## 1. 配置环境变量

复制 `.env.example` 为 `.env`，并填入你的 Tushare Token：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 数据源配置
TUSHARE_TOKEN=your_actual_token_here
TUSHARE_API_URL=https://tt.xiaodefa.cn  # 可选，使用自定义API地址
```

## 2. 获取 Tushare Token

1. 访问 [Tushare官网](https://tushare.pro/)
2. 注册账号并登录
3. 在个人中心获取 Token

## 3. 测试连接

### 测试 ETF 基础信息

```bash
python scripts/test_tushare.py --basic
```

### 测试 ETF 日线数据

```bash
# 获取最近30天数据
python scripts/test_tushare.py --etf-daily 159272.SZ

# 指定日期范围
python scripts/test_tushare.py --etf-daily 159272.SZ --start 20250101
```

### 测试股票日线数据

```bash
python scripts/test_tushare.py --stock-daily 000001.SZ --start 20250101
```

### 测试分钟线数据（需要高级权限）

```bash
python scripts/test_tushare.py --mins 159272.SZ --freq 5min --start "2026-05-20 09:30:00" --end "2026-05-20 15:00:00"
```

## 4. 使用示例

在代码中使用：

```python
from fund_quant.market.tushare_provider import (
    fetch_etf_basic,
    fetch_etf_daily,
    fetch_stock_daily,
    fetch_etf_minutes
)

# 获取 ETF 基础信息
df_basic = fetch_etf_basic()

# 获取 ETF 日线（自动缓存）
df_daily = fetch_etf_daily('159272.SZ', start_date='20250101')

# 获取股票日线
df_stock = fetch_stock_daily('000001.SZ', start_date='20250101')

# 获取分钟线
df_mins = fetch_etf_minutes('159272.SZ', freq='5min')
```

## 5. 功能特性

### 自动缓存

- 日线数据默认缓存 1 天
- 缓存文件保存在 `data/raw/cache/` 目录
- 支持强制刷新：`force_refresh=True`

### 频率限制处理

- 自动检测频率限制错误
- 触发限制后自动等待重试
- 最多重试 2 次

### 日志记录

- 使用统一的日志系统
- 记录所有 API 调用和错误
- 日志文件保存在 `logs/` 目录

## 6. 数据存储位置

```
data/
├── raw/
│   ├── tushare_etf_basic.csv          # ETF基础信息
│   └── cache/
│       ├── etf_daily/                  # ETF日线缓存
│       │   └── 159272.SZ_20250101_none.csv
│       └── stock_daily/                # 股票日线缓存
│           └── 000001.SZ_20250101_none.csv
```

## 7. 常见问题

### Q: 提示 "未配置 TUSHARE_TOKEN"

A: 请确保 `.env` 文件存在且包含正确的 Token

### Q: 提示 "频率限制"

A: 免费账号有调用频率限制，脚本会自动等待重试。建议：
- 使用缓存功能减少 API 调用
- 升级 Tushare 账号权限

### Q: 分钟线数据获取失败

A: 分钟线数据需要 Tushare 高级权限，请升级账号

### Q: 自定义 API 地址不生效

A: 确保 `.env` 中配置了 `TUSHARE_API_URL`，并重启程序

## 8. API 接口说明

### fetch_etf_basic()

获取所有 ETF 基础信息

**返回字段**：
- ts_code: ETF代码
- name: ETF名称
- market: 市场（SH/SZ）
- list_date: 上市日期
- fund_type: 基金类型

### fetch_etf_daily()

获取 ETF 日线行情

**参数**：
- ts_code: ETF代码
- start_date: 开始日期（YYYYMMDD）
- end_date: 结束日期（YYYYMMDD）
- use_cache: 是否使用缓存
- force_refresh: 是否强制刷新
- cache_expire_days: 缓存有效期（天）

**返回字段**：
- ts_code, trade_date, open, high, low, close
- pre_close, change, pct_chg, vol, amount

### fetch_stock_daily()

获取股票日线行情（参数和返回字段同 ETF）

### fetch_etf_minutes()

获取 ETF 分钟行情

**参数**：
- ts_code: ETF代码
- freq: 频率（1min/5min/15min/30min/60min）
- start_date: 开始时间（"YYYY-MM-DD HH:MM:SS"）
- end_date: 结束时间（"YYYY-MM-DD HH:MM:SS"）
