# 标题公司名识别实施进度更新

## ✅ 已完成（第1-4步）

### 1. TitleCompanyExtractor ✅
- 标题公司名提取器完成
- 4种格式识别
- 黑名单过滤

### 2. PaidContentDetector ✅
- 付费内容检测器完成
- 付费标题识别
- 隐藏股票检测

### 3. StockEntityResolver扩展 ✅
- ✅ 新增resolve_company_name()方法
- ✅ 补充14家公司到DEFAULT_SYMBOL_MAP
- ✅ 支持简称清洗
- ✅ 返回match_source和match_confidence

### 4. __init__.py更新 ✅
- ✅ 导出TitleCompanyExtractor
- ✅ 导出TitleCompanyCandidate

---

## 📋 剩余工作（第5-11步）

### 5. 集成到CLS pipeline ⏳
**关键文件**: 需要找到CLS的single_news_pipeline.py或后处理器

**需要**:
- [ ] 导入TitleCompanyExtractor和PaidContentDetector
- [ ] AI抽取后调用title_extractor.extract(title)
- [ ] 调用resolver.resolve_company_name()
- [ ] 合并到final_event.related_stocks
- [ ] 付费标题检测和降权

### 6-11. 剩余步骤
- [ ] 付费标题评分限高
- [ ] 高分无股票限分
- [ ] JSONL/CSV新增字段
- [ ] 回归测试
- [ ] 验收

---

## 🎯 当前进度: 4/11 (36%)

**下一步关键**: 找到CLS pipeline的后处理入口点

**预计剩余时间**: 1.5-2小时

---

**基础模块和核心方法已完成！需要继续集成到pipeline吗？**
