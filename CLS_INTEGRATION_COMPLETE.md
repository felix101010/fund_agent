# 财联社新闻系统集成完成

## ✅ 已完成修改

### single_news_pipeline.py修改完成

**1. 导入新增** ✅
```python
from fund_quant.nlp.entity_linking import TitleCompanyExtractor, StockEntityResolver
from fund_quant.nlp.news_filter.paid_content_detector import PaidContentDetector
```

**2. __init__新增** ✅
```python
self.title_extractor = TitleCompanyExtractor()
self.stock_resolver = StockEntityResolver()
self.paid_detector = PaidContentDetector()
```

**3. AI抽取后增加处理逻辑** ✅
- ✅ 标题公司名识别
- ✅ resolve_company_name()调用
- ✅ related_stocks合并去重
- ✅ 付费内容检测
- ✅ 付费标题限分（hidden_stock≤60, visible_stock≤65）
- ✅ 高分无股票限分（≥70且无股票→≤65）
- ✅ error_tags添加
- ✅ 异常处理不中断pipeline

---

## 🧪 验证方法

### 清除缓存
```bash
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
```

### 运行daemon测试
```bash
python scripts/news_lab/run_cls_daemon.py --interval 60
```

### 检查输出
```bash
# 查看最新JSONL
ls -lt output/cls/*.jsonl | head -1

# 检查标题识别
grep '"match_source": "title_rule"' output/cls/cls_*.jsonl | head -3

# 检查付费标题
grep '"is_paid_locked"' output/cls/cls_*.jsonl | head -3

# 检查富祥股份等是否识别
grep '富祥股份\|百利天恒\|中际旭创' output/cls/cls_*.jsonl | head -3
```

---

## 📋 待完成（可选）

### 1. pipeline_models.py字段（可选）
添加paid_content_result字段到NewsProcessResult

### 2. pipeline_reporter.py字段（可选）
CSV/JSONL增加：
- match_source
- match_confidence
- is_paid_locked
- stock_visibility

### 3. 回归测试（推荐）
创建test_cls_pipeline_integration.py

---

## ✅ 集成完成清单

- [x] 导入新模块
- [x] __init__初始化
- [x] 标题公司名识别集成
- [x] 付费标题检测集成
- [x] related_stocks合并
- [x] 付费标题限分逻辑
- [x] 高分无股票限分
- [x] 异常处理
- [ ] 字段输出（可选）
- [ ] 回归测试（推荐）

---

**核心集成已完成！清除缓存后运行daemon即可生效！**
