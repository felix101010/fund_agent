# 新闻 AI 事件抽取模块使用指南

## 📋 模块概述

新闻 AI 事件抽取模块负责将新闻转换成结构化事件，包括：
- 事件类型识别
- 情绪分析
- 主题识别
- 关联股票识别
- 事件级别评估
- 新颖性判断

## 🏗️ 架构

```
规则过滤 (news_filter)
    ↓ need_ai=True
AI 事件抽取 (news_ai)
    ↓
结构化事件 (news_event)
    ↓
入库/因子计算
```

## 📁 目录结构

```
src/fund_quant/nlp/
├── news_filter/              # 规则过滤（已实现）
│   ├── filter_models.py      # NewsItem, FilterResult
│   ├── keyword_rules.py
│   ├── rule_filter.py
│   └── news_filter_service.py
│
├── news_ai/                  # AI 事件抽取（本模块）
│   ├── ai_event_models.py    # AIEventResult, RelatedStock
│   ├── ai_event_extractor.py # AIEventExtractor
│   ├── ai_result_validator.py # AIResultValidator
│   └── prompt_builder.py     # PromptBuilder
│
└── news_event/               # 事件模型（用于入库）
    └── event_models.py       # NewsEvent
```

## 🚀 快速开始

### 1. 基础使用（Fallback 规则）

```python
from datetime import datetime
from fund_quant.nlp.news_filter import NewsItem, FilterResult, SimpleRuleFilter
from fund_quant.nlp.news_ai import AIEventExtractor

# 1. 规则过滤
filter = SimpleRuleFilter()
news = NewsItem(
    news_id="cls_12345",
    source="cls",
    title="生益科技M10覆铜板送样英伟达",
    content="生益科技宣布，公司M10覆铜板已成功送样英伟达，等待验证结果。",
    publish_time=datetime.now()
)

filter_result = filter.filter(news)

# 2. AI 事件抽取（不传 llm_client，使用 fallback 规则）
extractor = AIEventExtractor()

if extractor.should_extract(filter_result):
    event_result = extractor.extract(news, filter_result)
    
    print(f"事件类型: {event_result.event_type}")  # sample_delivery
    print(f"主题: {event_result.theme}")            # 英伟达M10材料
    print(f"情绪: {event_result.sentiment}")        # positive
    print(f"级别: {event_result.event_level}")      # A
    print(f"置信度: {event_result.confidence}")     # 0.80
    print(f"关联股票: {[s.name for s in event_result.related_stocks]}")
```

### 2. 使用 Ollama LLM

```python
from fund_quant.nlp.news_ai import AIEventExtractor, OllamaClient

# 使用 Ollama（需要先启动 Ollama 服务）
llm_client = OllamaClient(
    base_url="http://localhost:11434",
    model="qwen2.5:7b",  # 或 qwen2.5:1.5b, llama3.1:8b
    timeout=60
)

extractor = AIEventExtractor(llm_client=llm_client)
event_result = extractor.extract(news, filter_result)

# 查看结果
print(f"事件类型: {event_result.event_type}")
print(f"主题: {event_result.theme}")
print(f"情绪: {event_result.sentiment}")
print(f"级别: {event_result.event_level}")
print(f"置信度: {event_result.confidence}")
print(f"是否有效: {event_result.is_valid}")
```

### 3. 自定义 LLM 客户端

```python
from fund_quant.nlp.news_ai import AIEventExtractor

# 自定义 LLM 客户端（需要实现 generate 方法）
class MyLLMClient:
    def generate(self, prompt: str) -> str:
        # 调用 OpenAI/Claude/其他 API
        # 返回 JSON 字符串
        pass

llm_client = MyLLMClient()
extractor = AIEventExtractor(llm_client=llm_client)
event_result = extractor.extract(news, filter_result)
```

### 4. 批量处理

```python
from fund_quant.nlp.news_filter import NewsFilterService
from fund_quant.nlp.news_ai import AIEventExtractor

# 批量过滤
filter_service = NewsFilterService()
news_list = [...]  # 新闻列表
filter_results = filter_service.filter_news_batch(news_list)

# 批量抽取
extractor = AIEventExtractor()
event_results = []

for news, filter_result in zip(news_list, filter_results):
    if extractor.should_extract(filter_result):
        event_result = extractor.extract(news, filter_result)
        event_results.append(event_result)

# 筛选有效事件
valid_events = [e for e in event_results if e.is_valid]
```

## 📊 数据模型

### AIEventResult

```python
@dataclass
class AIEventResult:
    news_id: str                    # 新闻ID
    is_market_relevant: bool        # 是否有市场相关性
    event_type: str                 # 事件类型
    theme: str                      # 主题
    sub_themes: list[str]           # 子题材
    related_stocks: list[RelatedStock]  # 关联股票
    sentiment: str                  # positive/neutral/negative
    event_level: str                # S/A/B/C
    novelty_type: str               # 新颖性类型
    summary: str                    # 事件摘要
    confidence: float               # 置信度 0.0-1.0
    risk_flags: list[str]           # 风险标记
    raw_ai_response: str            # 原始 AI 输出
    is_valid: bool                  # 是否通过验证
    validation_errors: list[str]    # 验证错误
```

### 事件类型白名单

- `order_win` - 中标/订单
- `price_increase` - 涨价/提价
- `mass_production` - 量产
- `capacity_build` - 投产/扩产
- `verification_pass` - 验证通过/认证通过
- `sample_delivery` - 送样
- `supply_chain` - 进入供应链/供货
- `policy_release` - 政策发布
- `mna` - 并购重组
- `ipo` - IPO/上市辅导
- `risk_disconfirm` - 澄清/证伪
- `product_release` - 新品发布
- `technical_breakthrough` - 技术突破
- `strategic_cooperation` - 战略合作
- `general` - 普通事件

### 事件级别定义

- **S级**: 重大政策、全球首个、产业链核心重大变化、重大并购、确认进入全球核心客户供应链
- **A级**: 订单、中标、涨价、量产、验证通过、送样、进入供应链、重要客户合作、核心产品获批
- **B级**: 新品发布、战略合作、扩产、技术突破、试点、示范项目
- **C级**: 普通观点、一般会议、普通互动平台回复、泛泛表态

### 新颖性类型

- `new_theme` - 可能形成新题材
- `old_theme_new_progress` - 老题材出现新进展
- `old_theme_repeat` - 老题材重复信息
- `negative_disconfirm` - 证伪/澄清/风险新闻
- `noise` - 无交易价值噪音

## 🧪 Fallback 规则

当没有 LLM 客户端时，使用以下规则：

| 关键词 | event_type | sentiment | event_level |
|--------|-----------|-----------|-------------|
| 澄清/暂无相关业务 | risk_disconfirm | negative | A |
| 验证通过/认证通过 | verification_pass | positive | A |
| 送样 | sample_delivery | positive | A |
| 量产 | mass_production | positive | A |
| 中标/订单 | order_win | positive | A |
| 涨价/提价 | price_increase | positive | A |
| 战略合作 | strategic_cooperation | positive | B |

主题识别：
- 机器人/人形机器人 → 机器人
- 英伟达/M10 → 英伟达M10材料
- 芯片/半导体 → 半导体
- AI/算力 → AI算力
- 光模块/CPO → 光模块/CPO
- 卫星/商业航天 → 卫星产业

## ⚠️ 注意事项

1. **本模块不连接数据库**，只做纯事件抽取
2. **本模块不调用网络**，LLM 客户端由外部传入
3. **风险新闻特殊处理**：action="risk" 的新闻会被特别验证，不允许 sentiment="positive"
4. **validation_errors 包含警告和错误**：只有关键错误才导致 is_valid=False
5. **related_stocks 字段缺失不崩溃**：会用空字符串填充，但记录警告

## 🔗 下一步

事件抽取完成后，可以：
1. 将 `AIEventResult` 转换为 `NewsEvent` 入库
2. 基于事件结果计算主题强度因子
3. 结合行情数据验证事件影响
4. 生成交易信号

## 📝 测试

运行测试：
```bash
pytest tests/nlp/test_ai_event_extractor.py tests/nlp/test_ai_result_validator.py -v
```

所有测试通过 ✅ (22/22)
