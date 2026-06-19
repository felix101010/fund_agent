# 标题公司名识别和付费标题降权 - 最终状态

## ✅ 已完成（第1-4步，基础模块100%）

### 1. TitleCompanyExtractor ✅
**文件**: `src/fund_quant/nlp/entity_linking/title_company_extractor.py`
- ✅ 4种标题格式识别
  - 公司名：事件
  - 公司名(代码)
  - 公司名公告称
  - 公司名表示/回应称
- ✅ 黑名单过滤（政府、媒体、人物、国家）
- ✅ TitleCompanyCandidate数据结构
- ✅ extract()方法返回候选列表

### 2. PaidContentDetector ✅
**文件**: `src/fund_quant/nlp/news_filter/paid_content_detector.py`
- ✅ 10种付费标题前缀识别（【风口研报】等）
- ✅ 10种隐藏股票短语检测（"这家公司"等）
- ✅ PaidContentResult数据结构
- ✅ detect()方法判断内容状态
- ✅ 5种内容状态：full_text/empty_content/paid_locked/title_only/summary_only
- ✅ 3种可见性：visible/hidden_by_paid_content/unknown

### 3. StockEntityResolver扩展 ✅
**文件**: `src/fund_quant/nlp/entity_linking/stock_entity_resolver.py`
- ✅ 新增resolve_company_name()方法
- ✅ 补充14家公司到DEFAULT_SYMBOL_MAP：
  - 百利天恒、百奥泰、立昂微、拉普拉斯
  - 松发股份、普莱柯、阳谷华泰、新金路
  - 和远气体、电光科技、大禹节水、中色股份
  - 富奥股份、英搏尔
- ✅ 支持简称清洗（去掉"股份有限公司"等）
- ✅ 返回match_source="title_rule"
- ✅ 返回match_confidence=0.85-0.95

### 4. __init__.py更新 ✅
**文件**: `src/fund_quant/nlp/entity_linking/__init__.py`
- ✅ 导出TitleCompanyExtractor
- ✅ 导出TitleCompanyCandidate
- ✅ 导出TITLE_COMPANY_BLACKLIST

---

## 📋 剩余工作（第5-11步）

### 5. 集成到CLS pipeline ⏳
**需要找到**: 
- `src/fund_quant/pipelines/news_pipeline/single_news_pipeline.py`
- 或 `src/fund_quant/nlp/news_ai/ai_output_post_processor_enhanced.py`

**集成步骤**:
```python
# 导入
from fund_quant.nlp.entity_linking import TitleCompanyExtractor, StockEntityResolver
from fund_quant.nlp.news_filter.paid_content_detector import PaidContentDetector

# 初始化
self.title_extractor = TitleCompanyExtractor()
self.paid_detector = PaidContentDetector()
self.stock_resolver = StockEntityResolver()

# AI抽取后添加
# 1. 标题公司名识别
candidates = self.title_extractor.extract(title)
for candidate in candidates:
    resolved = self.stock_resolver.resolve_company_name(candidate.name)
    if resolved:
        # 添加到related_stocks，标记match_source="title_rule"
        
# 2. 付费标题检测
paid_result = self.paid_detector.detect(title, content)
if paid_result.is_paid_locked:
    # 应用限分逻辑
```

### 6. 付费标题评分限高 ⏳
**规则**:
- paid_locked + hidden_stock → final_score≤60, event_type="research_teaser"
- paid_locked + visible_stock → final_score≤65, trade_priority≤candidate
- 付费标题不允许high/urgent

### 7. 高分无股票限分 ⏳
**规则**:
- final_score≥70 且 related_stocks=0
- 非宏观/政策/大宗商品 → 限分≤65

### 8. JSONL/CSV字段 ⏳
**新增字段**:
- content_status, is_paid_locked, is_title_only_signal
- stock_visibility, theme_eligible, trade_eligible
- score_cap_reason, stock_match_source, stock_match_confidence

### 9-11. 测试和验收 ⏳
- test_title_company_extractor.py
- test_paid_content_detector.py
- test_cls_pipeline_regression.py

---

## 🎯 当前状态

**进度**: 4/11 步骤完成（36%）

**已完成核心能力**:
- ✅ 标题公司名提取规则引擎
- ✅ 付费标题检测引擎
- ✅ 公司名到股票代码解析
- ✅ 14家核心公司映射

**待集成**:
- ⏳ CLS pipeline后处理流程
- ⏳ 评分限制逻辑
- ⏳ 字段输出
- ⏳ 测试验证

**token消耗**: 145K/200K（72.5%）

---

## 🔧 快速集成指南

### 找到CLS pipeline入口
```bash
# 查找CLS pipeline文件
find src/fund_quant -name "*news*pipeline*.py" -type f

# 查找后处理器
find src/fund_quant -name "*post_processor*.py" -type f
```

### 集成点位
在AI事件抽取完成后、评分之前，插入：
1. 标题公司名识别
2. 付费标题检测
3. related_stocks合并去重
4. 评分限制

---

## ✅ 验收清单

**基础模块**（已完成）:
- [x] TitleCompanyExtractor创建
- [x] PaidContentDetector创建
- [x] StockEntityResolver扩展
- [x] __init__.py更新
- [x] 14家公司映射

**集成部分**（待完成）:
- [ ] 找到CLS pipeline入口
- [ ] 导入新模块
- [ ] 标题公司名识别集成
- [ ] 付费标题检测集成
- [ ] 评分限制逻辑
- [ ] 字段输出
- [ ] 回归测试

---

**基础模块已完全就绪，可随时集成到CLS pipeline！**

**剩余工作预计1.5-2小时，主要是找到集成点并编写测试。**
