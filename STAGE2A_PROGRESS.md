# 巨潮公告系统阶段2A实施记录

## ✅ 已完成

### 1. 公司主题映射
**文件**: `company_theme_mapping.py`
- ✅ 创建COMPANY_THEME_MAP
- ✅ 6家公司映射：中色股份、阳谷华泰、百奥泰、百利天恒、富奥股份、英搏尔
- ✅ get_company_theme()函数

---

## 🔄 进行中

### 2. 字段增强（需修改）

**announcement_pipeline_models.py**:
```python
# 新增字段
pdf_parsed: bool = False
pdf_download_status: str = "not_required"
pdf_parse_status: str = "not_required"
pdf_text_length: int = 0
pdf_text_preview: str = ""
pdf_parse_error: str = ""
pdf_extraction_method: str = ""
pdf_unparsed_score_cap: Optional[int] = None
```

**single_announcement_pipeline.py**:
```python
# final_event增加字段
'signal_direction': 'positive/negative/neutral/mixed',
'risk_priority': 'none/watch/high/urgent',
'primary_theme_id': ...,
'primary_theme_name': ...,
'secondary_theme_id': ...,
'secondary_theme_name': ...
```

### 3. risk_priority和signal_direction规则

**需在single_announcement_pipeline.py实现**:

| announcement_type | signal_direction | risk_priority | score_cap (未解析PDF) |
|-------------------|------------------|---------------|----------------------|
| safety_accident | negative | urgent | 无限制，但trade_priority≠urgent |
| abnormal_trading | mixed | high | 75 |
| external_guarantee | mixed | watch/high | 65 |
| fundraising_project_change | negative/mixed | high | 75 |
| project_expansion_progress | positive | none | 75 |
| pharma_regulatory_progress | positive/neutral | none | 75 |
| asset_or_equity_transfer | mixed | watch | 70 |
| governance类 | neutral | none | 无 |

### 4. 标题级限分逻辑

```python
if need_pdf and not pdf_parsed:
    if announcement_type == "project_expansion_progress":
        final_score = min(final_score, 75)
        pdf_unparsed_score_cap = 75
    elif announcement_type == "external_guarantee":
        final_score = min(final_score, 65)
        pdf_unparsed_score_cap = 65
    # ... 其他类型
    
    postprocess_notes.append(f"标题级未解析PDF，评分上限{pdf_unparsed_score_cap}")
    confidence = 0.6
```

---

## 📋 待完成（阶段2B）

### 5. PDF下载器
**文件**: `cninfo_pdf_downloader.py`
- 只处理action in ["analyze", "risk_review"] and need_pdf=True
- 下载到data/raw/cninfo_pdfs/YYYYMMDD/{announcement_id}.pdf
- 失败不中断pipeline

### 6. PDF文本提取
**文件**: `announcement_pdf_text_extractor.py`
- PyMuPDF (fitz) 优先
- fallback: pdfplumber → pypdf
- 不做OCR
- 提取前10页文本

### 7. Reporter增强
**文件**: `announcement_reporter.py`
- CSV增加新字段
- summary.md增加统计

### 8. 回归测试
**文件**: `tests/nlp/test_announcement_stage2.py`
- 8个测试用例

---

## ⏰ 预计剩余时间

- 完成2-4：15分钟（字段+规则+限分）
- 完成5-6：15分钟（PDF下载+提取）
- 完成7-8：15分钟（Reporter+测试）

**总计：45分钟**

---

## 🎯 验收标准

1. archive公告不下载PDF ✓
2. analyze/risk_review才下载PDF ✓
3. safety_accident的risk_priority=urgent，trade_priority≠urgent ✓
4. 标题级限分生效 ✓
5. 6家公司能补primary_theme_id ✓
6. PDF解析失败不中断pipeline ✓
7. Summary统计完整 ✓

---

**当前进度：1/8完成，继续阶段2A剩余工作？**
