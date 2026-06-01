# 系统架构文档

## 1. 系统概述

Fund Quant System 是一个机构级量化交易系统，专注于**新闻事件驱动的主题/ETF轮动策略**。

### 核心理念

```
海外事件 → 国内映射 → 主题轮动 → ETF配置
```

- **海外事件确认**: Reuters/Reddit/X 作为事实源
- **国内新闻验证**: 财联社/巨潮 作为情绪源
- **主题映射**: 海外公司 → A股主题 → ETF
- **量化执行**: 因子驱动的系统化交易

## 2. 系统架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    应用层 (Application)                   │
│  Dashboard | Signal API | Monitoring | Alert             │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    策略层 (Strategy)                      │
│  Theme Rotation | ETF Rotation | Event Driven           │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    因子层 (Factor)                        │
│  News Alpha | Momentum | Sentiment | Liquidity          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    特征层 (Feature)                       │
│  News Features | Market Features | Technical Features    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    数据层 (Data)                          │
│  Ingestion | Normalization | Storage | Quality           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Reuters  │     │  财联社   │     │  Tushare │
│ Reddit   │────▶│  巨潮     │────▶│  行情    │
│ Twitter  │     │  公告     │     │  基本面  │
└──────────┘     └──────────┘     └──────────┘
      │                │                 │
      └────────────────┼─────────────────┘
                       ↓
              ┌─────────────────┐
              │  Data Pipeline   │
              │  - 清洗          │
              │  - 去重          │
              │  - 标准化        │
              └─────────────────┘
                       ↓
              ┌─────────────────┐
              │   ClickHouse     │
              │   (时序存储)      │
              └─────────────────┘
                       ↓
              ┌─────────────────┐
              │  NLP Pipeline    │
              │  - 事件抽取      │
              │  - 情绪分析      │
              │  - 实体链接      │
              └─────────────────┘
                       ↓
              ┌─────────────────┐
              │ Feature Pipeline │
              │  - 新闻特征      │
              │  - 市场特征      │
              │  - 技术特征      │
              └─────────────────┘
                       ↓
              ┌─────────────────┐
              │ Factor Pipeline  │
              │  - 因子计算      │
              │  - 因子评估      │
              │  - 因子合成      │
              └─────────────────┘
                       ↓
              ┌─────────────────┐
              │ Signal Pipeline  │
              │  - 信号生成      │
              │  - 信号过滤      │
              │  - 信号排序      │
              └─────────────────┘
                       ↓
              ┌─────────────────┐
              │ Portfolio Mgmt   │
              │  - 组合构建      │
              │  - 风险控制      │
              │  - 再平衡        │
              └─────────────────┘
                       ↓
              ┌─────────────────┐
              │   Execution      │
              │  - 订单管理      │
              │  - 执行算法      │
              │  - 成本控制      │
              └─────────────────┘
```

## 3. 核心模块

### 3.1 数据系统 (data/)

**职责**: 多源数据采集、标准化、质量控制

```python
# 数据采集
from fund_quant.data.ingestion import ReutersCollector, CailianCollector

# 数据标准化
from fund_quant.data.normalization import NewsNormalizer

# 数据质量
from fund_quant.data.quality import DataQualityChecker
```

**关键特性**:
- 多源适配器模式
- 统一数据模型
- 自动去重
- 数据血缘追踪

### 3.2 NLP系统 (nlp/)

**职责**: 新闻理解、事件抽取、情绪分析

```python
# 事件抽取
from fund_quant.nlp.event_extraction import EventExtractor

# 情绪分析
from fund_quant.nlp.sentiment import SentimentAnalyzer

# 实体链接
from fund_quant.nlp.entity_linking import EntityLinker
```

**关键特性**:
- 规则 + LLM 混合
- 多语言支持
- 实体消歧
- 关系抽取

### 3.3 知识库 (knowledge/)

**职责**: 维护主题-行业-个股-ETF映射关系

```python
# 主题映射
from fund_quant.knowledge.themes import ThemeMapper

# ETF映射
from fund_quant.knowledge.etfs import ETFMapper
```

**数据结构**:
```
海外公司 → A股主题 → A股ETF
  Nvidia → AI芯片   → 159813.SZ
        → 半导体    → 512480.SH
        → 算力      → 515980.SH
```

### 3.4 特征工程 (features/)

**职责**: 从原始数据构建特征

```python
# 新闻特征
from fund_quant.features.news_features import NewsFeatureBuilder

# 市场特征
from fund_quant.features.market_features import MarketFeatureBuilder
```

**特征类型**:
- 新闻特征: 事件频率、情绪得分、重要性
- 市场特征: 收益率、波动率、成交额
- 流动性特征: 换手率、买卖价差
- 技术特征: MA、MACD、RSI

### 3.5 因子研究 (factors/)

**职责**: 因子计算、评估、合成

```python
# 新闻Alpha因子
from fund_quant.factors.news_alpha import NewsAlphaFactor

# 动量因子
from fund_quant.factors.momentum import MomentumFactor
```

**因子评估指标**:
- IC (信息系数)
- IR (信息比率)
- Turnover (换手率)
- Sharpe Ratio

### 3.6 策略引擎 (strategy/)

**职责**: 信号生成、组合构建

```python
# 主题轮动策略
from fund_quant.strategy.theme_rotation import ThemeRotationStrategy

# ETF轮动策略
from fund_quant.strategy.etf_rotation import ETFRotationStrategy
```

**策略类型**:
- 主题轮动: 基于新闻热度的主题切换
- ETF轮动: 基于动量的ETF配置
- 事件驱动: 基于重大事件的快速响应

### 3.7 风控系统 (risk/)

**职责**: 风险监控、仓位管理

```python
# 风险引擎
from fund_quant.risk.risk_engine import RiskEngine

# 仓位限制
from fund_quant.risk.position_limit import PositionLimiter
```

**风控规则**:
- 单主题最大仓位: 30%
- 单ETF最大仓位: 20%
- 最大回撤: 15%
- 止损线: -5%

### 3.8 回测系统 (backtest/)

**职责**: 高保真回测、性能评估

```python
# 回测引擎
from fund_quant.backtest.engine import BacktestEngine

# 成本模型
from fund_quant.backtest.cost_model import CostModel
```

**回测特性**:
- 事件驱动架构
- 真实成本模拟
- 滑点模型
- Walk-Forward验证

## 4. 数据模型

### 4.1 原始新闻 (raw_news)

```sql
CREATE TABLE raw_news (
    id String,
    source String,
    title String,
    summary String,
    content String,
    url String,
    published_at DateTime,
    collected_at DateTime,
    language String,
    raw_json String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(published_at)
ORDER BY (source, published_at, id);
```

### 4.2 提取事件 (extracted_events)

```sql
CREATE TABLE extracted_events (
    news_id String,
    event_type String,
    companies Array(String),
    themes Array(String),
    sentiment String,
    importance_score UInt8,
    confidence Float32,
    a_share_mapping UInt8,
    related_etfs Array(String),
    extracted_at DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(extracted_at)
ORDER BY (event_type, extracted_at);
```

### 4.3 因子数据 (factors)

```sql
CREATE TABLE factors (
    date Date,
    asset_code String,
    asset_type String,
    factor_name String,
    factor_value Float64,
    created_at DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, asset_code, factor_name);
```

## 5. 部署架构

### 5.1 服务组件

```
┌─────────────────────────────────────────────┐
│              Load Balancer                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│          API Gateway (FastAPI)               │
└─────────────────────────────────────────────┘
                    ↓
┌──────────────┬──────────────┬──────────────┐
│ Data Service │Signal Service│ Trade Service│
└──────────────┴──────────────┴──────────────┘
                    ↓
┌──────────────┬──────────────┬──────────────┐
│ ClickHouse   │    Redis     │  PostgreSQL  │
└──────────────┴──────────────┴──────────────┘
```

### 5.2 监控体系

```
Prometheus (指标采集)
    ↓
Grafana (可视化)
    ↓
AlertManager (告警)
    ↓
钉钉/企业微信 (通知)
```

## 6. 开发流程

### 6.1 研究流程

```
1. 数据探索 (notebooks/)
2. 因子开发 (factors/)
3. 回测验证 (backtest/)
4. 策略封装 (strategy/)
5. 生产部署 (pipelines/)
```

### 6.2 代码规范

- 使用 Black 格式化
- 使用 Ruff 检查
- 使用 MyPy 类型检查
- 单元测试覆盖率 > 80%

## 7. 性能指标

### 7.1 系统性能

- 新闻采集延迟: < 5分钟
- 事件抽取延迟: < 30秒
- 因子计算延迟: < 1分钟
- 信号生成延迟: < 10秒

### 7.2 策略性能

- 年化收益: > 15%
- 最大回撤: < 15%
- Sharpe Ratio: > 1.5
- 胜率: > 55%

## 8. 安全与合规

- 数据加密存储
- API访问鉴权
- 操作审计日志
- 风控熔断机制

## 9. 扩展性

- 水平扩展: 支持多实例部署
- 数据分片: ClickHouse 分布式表
- 缓存层: Redis 集群
- 消息队列: Kafka (可选)

## 10. 参考资料

- [数据字典](data_dictionary.md)
- [因子库](factor_library.md)
- [策略设计](strategy_design.md)
- [风控政策](risk_policy.md)
- [部署指南](deployment.md)
