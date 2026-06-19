# CLS 新闻规则修复 - 实施总结

**日期**: 2026-06-17  
**状态**: ✅ 核心功能已完成，测试通过

## 已完成的功能

### 1. ✅ normalized_title 生成

**位置**: `src/fund_quant/data_sources/news/cls_api_collector.py`

**函数**: `build_normalized_title(title: str, content: str, max_len: int = 60) -> str`

**功能**:
- 如果 title 非空，清洗后返回
- 如果 title 为空，从 content 生成：
  - 移除"财联社X月X日电，"前缀
  - 移除【xxx】标签
  - 截取前60个字符

**集成**: 已在 `_parse_item` 方法中自动生成 `normalized_title` 字段

### 2. ✅ 股票代码硬解析

**位置**: `src/fund_quant/nlp/news_filter/keyword_rules.py`

**函数**: `extract_stocks_by_code_pattern(text: str) -> list[dict]`

**功能**:
- 正则匹配：`公司名(股票代码)` 格式
- 支持中英文括号
- 自动补全 A股后缀（6开头→.SH，0/3开头→.SZ，8/4开头→.BJ）
- 支持港股/美股格式

**返回**:
```python
[{
    "code": "600196.SH",
    "name": "复星医药",
    "market": "A股",
    "match_type": "name_code_pattern",
    "confidence": 1.0
}]
```

### 3. ✅ 付费研报标题处理

**位置**: `src/fund_quant/nlp/news_filter/paid_content_detector.py`

**函数**: 
- `is_paid_research_teaser(text: str) -> bool`
- `classify_paid_research_teaser(item: dict) -> dict`

**识别关键词**:
- 电报解读、风口研报、公告全知道、盘中宝、狙击龙虎榜
- 研报、强call、这家公司、该公司、业内称、分析师称

**输出字段**:
```python
{
    "event_type": "paid_research_teaser",
    "ai_level": "light",
    "need_ai": True,
    "trade_priority": "watch",
    "confidence": 0.55,
    "can_trade_directly": False,
    "need_manual_followup": True,
    "manual_followup_reason": "标题隐藏公司名，正文为空或信息不完整，无法确认标的",
    "risk_flags": ["teaser_no_full_content", "hidden_stock"],
    "theme_ids": [...],  # 从标题提取
    "theme_names": [...],
    "related_stocks": []  # 如果没有明确股票代码，保持为空
}
```

### 4. ✅ 海外 AI 基建主题映射

**位置**: `src/fund_quant/nlp/news_filter/keyword_rules.py`

**函数**: `classify_overseas_ai_infrastructure(item: dict) -> Optional[dict]`

**匹配条件**:
1. AI基建关键词：数据中心、AI基础设施、GPU集群、算力基础设施
2. 海外公司关键词：英伟达、谷歌、微软、Meta、Equinix、思科
3. 动作关键词：投资、扩建、合作、发债、订单

**事件类型映射**:
- 发债/筹资/融资 → `financing_for_ai_capex` (50分, watch, light)
- 订单/采购 → `order_win` (70分, candidate, deep)
- 投资/扩建/建设 → `ai_infrastructure_investment` (65分, candidate, light)
- 携手/合作/部署 → `strategic_cooperation` (65分, candidate, light)

**主题**: 统一映射到 `ai_compute` (AI算力)

### 5. ✅ 战争无人机主题修正

**位置**: `src/fund_quant/nlp/news_filter/keyword_rules.py`

**函数**: `fix_war_drone_theme(item: dict) -> dict`

**修正逻辑**:
- 如果 `primary_theme_id == "low_altitude_economy"`
- 且文本包含"无人机"
- 且文本包含战争关键词（俄罗斯、乌克兰、伊朗、导弹、袭击、炼油厂）

则修正为:
```python
{
    "event_type": "geopolitical_risk",
    "primary_theme_id": "energy_risk" 或 None,  # 如果涉及能源关键词
    "primary_theme_name": "能源风险" 或 None,
    "trade_priority": "watch",
    "final_score": 40,
    "ai_level": "none",
    "need_ai": False,
    "risk_flags": ["geopolitical_conflict", "war_drone_not_low_altitude"]
}
```

### 6. ✅ ai_level 分级处理

**位置**: `src/fund_quant/nlp/news_filter/keyword_rules.py`

**函数**: `apply_ai_level(item: dict) -> dict`

**分级规则**:
- `none`: 不需要AI（战争无人机、general低分、宏观数据）
- `light`: 轻量AI（付费研报、海外AI基建无A股、低分有股票）
- `deep`: 深度AI（强催化剂、高分有股票）
- `urgent`: 紧急AI（预留）

**兼容性**: `need_ai = ai_level in ['light', 'deep', 'urgent']`

## 测试覆盖

**测试文件**: `tests/test_cls_news_rule_fixes.py`

**测试数量**: 22个测试，全部通过 ✅

| 测试类 | 测试数量 | 状态 |
|--------|----------|------|
| TestNormalizedTitle | 3 | ✅ |
| TestStockCodeExtractor | 5 | ✅ |
| TestPaidResearchTeaser | 3 | ✅ |
| TestOverseasAIInfrastructure | 3 | ✅ |
| TestWarDroneFix | 3 | ✅ |
| TestAILevel | 5 | ✅ |

## 集成指南

### 步骤 1: CLS 原始新闻采集

已自动集成，`cls_api_collector.py` 的 `_parse_item` 方法会自动生成 `normalized_title`。

### 步骤 2: 规则过滤流程（需要手动集成）

在现有的 `rule_filter.py` 或 `news_filter_service.py` 中，按以下顺序调用：

```python
from fund_quant.nlp.news_filter.keyword_rules import (
    extract_stocks_by_code_pattern,
    classify_overseas_ai_infrastructure,
    fix_war_drone_theme,
    apply_ai_level,
)
from fund_quant.nlp.news_filter.paid_content_detector import (
    is_paid_research_teaser,
    classify_paid_research_teaser,
)

def process_cls_news(item: dict) -> dict:
    """处理单条 CLS 新闻"""
    
    # 1. 构建完整文本（使用 normalized_title）
    text = f"{item.get('normalized_title', '')} {item.get('title', '')} {item.get('content', '')}"
    
    # 2. 股票代码硬解析（规则层提取）
    rule_stocks = extract_stocks_by_code_pattern(text)
    if rule_stocks:
        item['related_stocks'] = rule_stocks
        item['related_stocks_count'] = len(rule_stocks)
    else:
        item['related_stocks'] = []
        item['related_stocks_count'] = 0
    
    # 3. 判断是否付费研报
    if is_paid_research_teaser(text):
        item = classify_paid_research_teaser(item)
        item = apply_ai_level(item)
        return item  # 付费研报直接返回，不进入普通流程
    
    # 4. 海外 AI 基建主题
    ai_infra_result = classify_overseas_ai_infrastructure(item)
    if ai_infra_result:
        item.update(ai_infra_result)
    
    # 5. 现有规则过滤（rule_filter.filter）
    # ... 现有逻辑 ...
    
    # 6. AI 处理（如果 need_ai=True）
    # ... 现有 AI 逻辑 ...
    # 注意：AI 输出的 related_stocks 只能补充，不能删除规则层识别的
    
    # 7. 战争无人机修正（后处理）
    item = fix_war_drone_theme(item)
    
    # 8. ai_level 计算
    item = apply_ai_level(item)
    
    # 9. 更新 related_stocks_count
    item['related_stocks_count'] = len(item.get('related_stocks', []))
    
    return item
```

### 步骤 3: AI 后处理（需要手动集成）

在 `ai_output_post_processor_enhanced.py` 中，确保：

```python
def merge_ai_stocks_with_rule_stocks(rule_stocks: list, ai_stocks: list) -> list:
    """
    合并规则层和AI提取的股票
    
    规则：
    1. 规则层提取的股票（match_type="name_code_pattern"）优先级最高
    2. AI 只能补充，不能删除规则层股票
    3. 按 code 去重
    """
    merged = {}
    
    # 先加入规则层股票
    for stock in rule_stocks:
        if stock.get('match_type') == 'name_code_pattern':
            merged[stock['code']] = stock
    
    # 再加入 AI 股票（如果不重复）
    for stock in ai_stocks:
        code = stock.get('code')
        if code and code not in merged:
            merged[code] = stock
    
    return list(merged.values())
```

### 步骤 4: 输出字段补全

确保所有新闻输出包含以下字段：

```python
{
    "news_id": "",
    "source": "cls",
    "title": "",
    "normalized_title": "",  # 新增
    "content": "",
    "publish_time": "",
    "event_type": "",
    "primary_theme_id": "",
    "primary_theme_name": "",
    "theme_ids": [],  # 新增
    "theme_names": [],  # 新增
    "catalyst": "",  # 新增
    "supply_chain_position": "",  # 新增
    "trade_priority": "",
    "final_score": 0,
    "confidence": 0.0,
    "ai_level": "none",  # 新增
    "need_ai": False,
    "can_trade_directly": False,  # 新增
    "need_manual_followup": False,  # 新增
    "manual_followup_reason": "",  # 新增
    "related_stocks": [],
    "related_stocks_count": 0,
    "related_etfs": [],
    "risk_flags": [],
    "error_tags": []
}
```

## 验收标准

### 已完成 ✅

1. ✅ normalized_title 生成函数已实现
2. ✅ 股票代码硬解析已实现
3. ✅ 付费研报分类已实现
4. ✅ 海外 AI 基建主题映射已实现
5. ✅ 战争无人机修正已实现
6. ✅ ai_level 分级已实现
7. ✅ 所有测试通过（22/22）

### 待集成 ⚠️

需要手动集成到现有的新闻处理流程：

1. ⚠️ 在 `rule_filter.py` 或处理入口调用新增的规则函数
2. ⚠️ 在 `ai_output_post_processor_enhanced.py` 中保护规则层提取的股票
3. ⚠️ 确保输出字段完整

## 如何测试集成

运行测试：
```bash
pytest tests/test_cls_news_rule_fixes.py -v
```

期望结果：22 passed ✅

## 核心原则

1. **规则优先，AI补充** - 股票代码硬解析不被AI覆盖
2. **付费标题独立处理** - 不让AI猜隐藏股票
3. **主题补全** - 海外AI基建映射到ai_compute
4. **误判修正** - 战争无人机不是低空经济
5. **分级处理** - ai_level 精细控制AI资源

## 下一步

1. 在实际 CLS pipeline 中集成这些规则
2. 运行实际数据验证效果
3. 根据错例继续优化规则
4. 逐步完善主题词库和催化剂识别

所有核心功能已实现，测试通过，可以进行集成！🚀
