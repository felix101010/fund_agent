# 标题公司名识别和付费标题降权实施进度

## ✅ 已完成（第1-2步）

### 1. title_company_extractor.py
**位置**: `src/fund_quant/nlp/entity_linking/title_company_extractor.py`

**功能**:
- ✅ 4种标题格式识别（公司名：、公司名(代码)、公司名公告称、公司名表示）
- ✅ 黑名单过滤（政府、媒体、人物、国家）
- ✅ TitleCompanyCandidate输出结构
- ✅ extract()方法

### 2. paid_content_detector.py
**位置**: `src/fund_quant/nlp/news_filter/paid_content_detector.py`

**功能**:
- ✅ 付费标题前缀识别（【风口研报】等10种）
- ✅ 隐藏股票短语检测（"这家公司"等10种）
- ✅ PaidContentResult输出结构
- ✅ detect()方法
- ✅ 内容状态判断（paid_locked/summary_only/full_text）

---

## 📋 待完成（第3-11步）

### 3. 扩展StockEntityResolver
**文件**: `src/fund_quant/nlp/entity_linking/stock_entity_resolver.py`

**需要**:
- [ ] 新增resolve_company_name()方法
- [ ] 补充DEFAULT_SYMBOL_MAP（百利天恒、百奥泰、立昂微等14家公司）
- [ ] 支持简称清洗（去掉"股份有限公司"等）
- [ ] 返回match_source和match_confidence

### 4. 更新__init__.py
**文件**: `src/fund_quant/nlp/entity_linking/__init__.py`

**需要**:
```python
from .title_company_extractor import TitleCompanyExtractor, TitleCompanyCandidate
```

### 5. 集成到CLS pipeline后处理
**文件**: `src/fund_quant/pipelines/news_pipeline/single_news_pipeline.py`

**需要**:
- [ ] 导入TitleCompanyExtractor和PaidContentDetector
- [ ] AI抽取后增加标题公司名识别
- [ ] 付费标题检测和降权
- [ ] related_stocks去重合并
- [ ] match_source="title_rule"标记

### 6. 付费标题评分限高
**位置**: single_news_pipeline或后处理器

**规则**:
- [ ] paid_locked + hidden_stock → final_score≤60, event_type="research_teaser"
- [ ] paid_locked + visible_stock → final_score≤65, trade_priority≤candidate
- [ ] 付费标题不允许high/urgent

### 7. 高分无股票限分
**规则**:
- [ ] final_score≥70 且 related_stocks=0 → 限分≤65
- [ ] 宏观政策/大宗商品除外
- [ ] error_tags添加score_capped_no_stock

### 8. JSONL/CSV新增字段
**需要在reporter中添加**:
- [ ] content_status
- [ ] is_paid_locked
- [ ] is_title_only_signal
- [ ] stock_visibility
- [ ] theme_eligible
- [ ] trade_eligible
- [ ] score_cap_reason
- [ ] stock_match_source
- [ ] stock_match_confidence

### 9-10. 回归测试
**文件**: 
- [ ] tests/nlp/test_title_company_extractor.py
- [ ] tests/nlp/test_paid_content_detector.py
- [ ] tests/nlp/test_cls_pipeline_regression.py

**测试用例**:
1. 富祥股份标题识别
2. 百利天恒标题识别
3. 百奥泰标题识别
4. 中际旭创标题识别
5. 付费隐藏股票标题
6. 高分无股票限分

### 11. 验收
- [ ] 运行pytest测试
- [ ] 运行CLS批处理
- [ ] 验证related_stocks不再为空
- [ ] 验证付费标题不再high/urgent
- [ ] 验证JSONL/CSV新增字段

---

## 🎯 下一步建议

**快速路径**（优先级排序）:
1. **扩展StockEntityResolver**（第3步）- 核心逻辑
2. **集成到CLS pipeline**（第5步）- 接入点
3. **付费标题限分**（第6步）- 降权逻辑
4. **高分无股票限分**（第7步）- 补充规则
5. **测试验证**（第9-11步）

**预计工作量**: 2-3小时

---

## 📁 文件清单

**已创建**:
- ✅ src/fund_quant/nlp/entity_linking/title_company_extractor.py
- ✅ src/fund_quant/nlp/news_filter/paid_content_detector.py

**需修改**:
- ⏳ src/fund_quant/nlp/entity_linking/stock_entity_resolver.py
- ⏳ src/fund_quant/nlp/entity_linking/__init__.py
- ⏳ src/fund_quant/pipelines/news_pipeline/single_news_pipeline.py
- ⏳ src/fund_quant/pipelines/news_pipeline/news_reporter.py（或对应reporter）

**需创建测试**:
- ⏳ tests/nlp/test_title_company_extractor.py
- ⏳ tests/nlp/test_paid_content_detector.py
- ⏳ tests/nlp/test_cls_pipeline_regression.py

---

**第1-2步已完成，基础模块就绪！需要继续吗？**
