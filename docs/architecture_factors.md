# 因子计算模块架构文档

## 架构概述

主题因子计算模块采用分层架构设计，将核心计算逻辑从 scripts 目录迁移到 `src/fund_quant/factors/` 模块，实现代码复用和职责分离。

## 目录结构

```
src/fund_quant/factors/
├── __init__.py                   # 模块导出
├── models.py                     # 数据模型定义
├── factor_utils.py               # 通用因子计算函数
└── theme_daily_factors.py        # 主题因子计算器

scripts/
└── calculate_theme_factors.py    # 薄入口脚本（命令行接口）
```

## 分层职责

### 1. models.py - 数据模型层

**职责**：定义主题因子的数据结构和字段规范

**核心内容**：
- `ThemeDailyFactor`: 主题日度因子数据类
- `FACTOR_COLUMNS`: 标准化的因子列名列表（34个字段）

**字段分类**：
- 基础信息：trade_date, theme_id, theme_name, index_symbol, etf_symbol
- 价格：index_close, etf_close
- 收益率：ret_1d, ret_3d, ret_5d, ret_20d, ret_60d
- 基准收益率：hs300_ret_5d, hs300_ret_20d, hs300_ret_60d
- Alpha：alpha_5d, alpha_20d, alpha_60d
- 成交额指标：etf_amount, amount_ma5, amount_ma20, amount_ratio_1d, amount_ratio_5d
- 均线：index_ma5, index_ma10, index_ma20, index_ma30, index_ma60, index_ma250
- 趋势信号：above_ma20, above_ma60, ma20_gt_ma60, ma5_gt_ma20, trend_score

### 2. factor_utils.py - 通用因子函数库

**职责**：封装可复用的因子计算逻辑

**核心函数**：

#### `calculate_returns(df, periods=[1,3,5,20,60]) -> DataFrame`
- 计算多周期收益率
- 公式：(close / close.shift(period) - 1) * 100
- 返回字段：ret_1d, ret_3d, ret_5d, ret_20d, ret_60d

#### `calculate_moving_averages(df, windows=[5,10,20,30,60,250]) -> DataFrame`
- 计算移动均线
- 方法：rolling().mean()
- 返回字段：ma5, ma10, ma20, ma30, ma60, ma250

#### `calculate_alpha(theme_df, benchmark_df, periods=[5,20,60]) -> DataFrame`
- 计算超额收益（Alpha）
- 公式：theme_return - benchmark_return
- 按 trade_date 对齐数据
- 返回字段：alpha_5d, alpha_20d, alpha_60d

#### `calculate_amount_ratio(df, short_window=5, long_window=20) -> DataFrame`
- 计算成交额倍数
- 短期窗口：5日，长期窗口：20日
- 公式：amount / amount_ma20, amount_ma5 / amount_ma20
- 避免除以0处理
- 返回字段：amount_ma5, amount_ma20, amount_ratio_1d, amount_ratio_5d

#### `calculate_trend_score(df) -> DataFrame`
- 计算趋势得分（0-4分）
- 评分规则：
  - +1: 价格在MA20上方
  - +1: 价格在MA60上方
  - +1: MA20在MA60上方
  - +1: MA5在MA20上方
- 返回字段：above_ma20, above_ma60, ma20_gt_ma60, ma5_gt_ma20, trend_score

**设计原则**：
- 所有函数使用类型注解
- 详细的 docstring 说明
- 对 NaN 值保持原样，不做填充
- 避免除以0错误
- 按 trade_date 升序排序

### 3. theme_daily_factors.py - 业务编排层

**职责**：协调数据读取、因子计算、结果输出

#### `ThemeDailyFactorCalculator` 类

**初始化参数**：
- `clickhouse_client`: ClickHouse客户端
- `theme_config`: 主题配置DataFrame
- `benchmark_symbol`: 基准指数代码（默认"000300.SH"）

**核心方法**：

##### `calculate(start_date, end_date, theme_ids) -> DataFrame`
完整的因子计算流程：
1. 加载主题配置
2. 获取基准数据（沪深300）
3. 逐个主题计算因子
4. 合并所有主题数据
5. 输出统计信息

##### `_calculate_one_theme(...) -> DataFrame`
计算单个主题的因子：
1. 获取指数日线数据
2. 获取ETF日线数据
3. 计算指数指标（收益率、均线、趋势）
4. 计算ETF成交额指标
5. 按日期对齐指数和ETF
6. 合并基准数据并计算Alpha
7. 添加主题信息
8. 删除数据不足的行

##### `_fetch_daily_bars(symbol, asset_type, start_date, end_date) -> DataFrame`
从数据库读取日线数据：
- 自动扩展查询范围（往前400天以保证MA250计算）
- 转换数据类型（日期、数值）
- 按 trade_date 排序

#### `load_theme_config(config_path) -> DataFrame`
加载主题配置文件：
- 读取 theme_etf_mapping.yaml
- 解析为 DataFrame
- 包含字段：theme_id, theme_name, index_symbol, etf_symbol

### 4. scripts/calculate_theme_factors.py - 入口脚本层

**职责**：命令行参数解析、调用服务、结果展示

**命令行参数**：
- `--days N`: 计算最近N天数据
- `--start-date YYYY-MM-DD`: 开始日期
- `--end-date YYYY-MM-DD`: 结束日期
- `--theme THEME_ID`: 只计算指定主题
- `--dry-run`: Dry-run模式（不写入数据库）

**执行流程**：
1. 解析命令行参数
2. 连接ClickHouse
3. 加载主题配置
4. 初始化因子计算器
5. 执行计算
6. Dry-run模式：显示统计信息
7. 正常模式：写入数据库

**Dry-run输出**：
- 计算主题数量
- 生成因子行数
- 最新交易日
- Top 10 ret_5d
- Top 10 alpha_20d
- Top 10 amount_ratio_1d

## 数据流

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 命令行入口 (scripts/calculate_theme_factors.py)          │
│    - 解析参数                                                │
│    - 加载配置                                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 因子计算器 (ThemeDailyFactorCalculator)                  │
│    - 读取daily_bars (指数/ETF/基准)                          │
│    - 调用因子计算函数                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 因子计算函数 (factor_utils)                              │
│    - calculate_returns()                                    │
│    - calculate_moving_averages()                            │
│    - calculate_alpha()                                      │
│    - calculate_amount_ratio()                               │
│    - calculate_trend_score()                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 结果输出                                                  │
│    - Dry-run: 打印统计信息                                   │
│    - 正常: 写入theme_daily_factors表                         │
└─────────────────────────────────────────────────────────────┘
```

## 使用示例

### 计算所有主题（最近30天）
```bash
uv run python scripts/calculate_theme_factors.py --days 30
```

### 计算指定日期范围
```bash
uv run python scripts/calculate_theme_factors.py --start-date 2026-01-01 --end-date 2026-06-01
```

### 只计算指定主题
```bash
uv run python scripts/calculate_theme_factors.py --theme ai --days 30
```

### Dry-run验证
```bash
uv run python scripts/calculate_theme_factors.py --dry-run --days 10
```

## 数据库表结构

### daily_bars（输入）
存储原始日线数据：
- 主题指数：asset_type='INDEX'
- 主题ETF：asset_type='ETF'
- 沪深300基准：symbol='000300.SH', asset_type='INDEX'

### theme_daily_factors（输出）
存储计算后的因子数据：
- 引擎：ReplacingMergeTree(created_at)
- 排序键：ORDER BY (trade_date, theme_id)
- 字段：34个因子字段
- 去重：写入前删除日期范围内的旧数据

## 重构收益

### 1. 架构清晰
- 职责分离：入口/业务/计算/模型 四层
- 代码复用：通用函数可被其他模块调用
- 易于测试：每层可独立测试

### 2. 可维护性
- 核心逻辑集中在 factors 模块
- 修改计算逻辑不需要改 scripts
- 类型注解和文档完善

### 3. 可扩展性
- 新增因子：在 factor_utils 添加函数
- 新增因子类型：参考 ThemeDailyFactorCalculator 创建新类
- 新增数据源：修改 _fetch_daily_bars 方法

### 4. 用户友好
- 支持多种参数组合
- Dry-run模式验证计算
- 清晰的日志输出
- 详细的统计信息

## 技术要点

### 1. 数据对齐
- 指数、ETF、基准按 trade_date 对齐
- 使用 inner join 确保数据完整性
- 删除前期数据不足的行（ret_60d, index_ma60）

### 2. NaN 处理
- 保持 NaN 原样，不做填充
- 只在必要时删除 NaN 行
- 避免除以0错误（使用 np.where）

### 3. 性能优化
- 批量读取数据
- 扩展查询范围减少数据库请求
- 批量写入数据库（10000行/批）

### 4. 数据去重
- 写入前删除日期范围内的旧数据
- ReplacingMergeTree自动去重
- 支持增量更新

## 验证结果

重构后运行 `--dry-run --days 10`：
- ✅ 计算19个主题（3个主题数据缺失）
- ✅ 生成3618行因子数据
- ✅ 最新交易日：2026-06-01
- ✅ 收益率、Alpha、成交额倍数正常
- ✅ 写入数据库成功
- ✅ 排名查询正常

## 未来扩展

1. **更多因子**：动量、波动率、相关性
2. **更多周期**：周度、月度因子
3. **更多资产**：个股、行业因子
4. **因子合成**：多因子加权、机器学习
5. **因子回测**：历史表现分析
