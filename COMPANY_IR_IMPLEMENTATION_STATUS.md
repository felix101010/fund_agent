# Company IR 新闻源实施状态

## ✅ 已完成（2/9模块）

### 1. ir_company_config.py ✅
**位置**: `src/fund_quant/data_sources/news/company_ir/ir_company_config.py`
- ✅ IR_COMPANIES配置（NVDA/TSLA/AAPL/MSFT）
- ✅ get_ir_company_config()
- ✅ list_enabled_ir_tickers()

### 2. ir_rules.py ✅
**位置**: `src/fund_quant/data_sources/news/company_ir/ir_rules.py`
- ✅ IRRules分类器
- ✅ 7条规则（earnings_release/earnings_event/investor_material等）
- ✅ classify()方法

---

## 📋 待完成（7/9模块）

### 3. ir_rss_collector.py ⏳
**需要**:
```python
class IRRSSCollector:
    def collect(self, ticker: str, days: int = 30) -> list[dict]:
        # 使用feedparser抓取RSS
        # 返回原始item列表
```

### 4. ir_page_collector.py ⏳
**需要**:
```python
class IRPageCollector:
    def fetch_article(self, url: str) -> dict:
        # requests + BeautifulSoup
        # 提取content和attachments
```

### 5. ir_document_downloader.py ⏳
**需要**:
```python
class IRDocumentDownloader:
    def download_attachments(ticker, date, attachments) -> list[dict]:
        # 下载PDF到data/company_ir/{ticker}/{date}/
```

### 6. ir_normalizer.py ⏳
**需要**:
```python
def normalize_ir_item(ticker, config, raw_item, article_detail) -> dict:
    # 标准化输出，兼容news/models.py
    # 生成稳定news_id
```

### 7. __init__.py ⏳
**需要**:
```python
from .ir_rss_collector import IRRSSCollector
from .ir_rules import IRRules
from .ir_company_config import get_ir_company_config

__all__ = [...]
```

### 8. README.md ⏳
**需要**: 使用说明和架构文档

### 9. scripts/collect_company_ir.py ⏳
**需要**: CLI脚本（--tickers, --days, --save-json等）

---

## 🧪 测试待创建

### tests/test_company_ir_config.py ⏳
- [ ] list_enabled包含4家公司
- [ ] get_ir_company_config("nvda")返回NVIDIA

### tests/test_company_ir_rules.py ⏳
- [ ] "Financial Results" → earnings_release/90分
- [ ] "will release" → earnings_date_announcement/65分
- [ ] "investor presentation" → investor_material/80分
- [ ] "dividend" → capital_return/80分

### tests/test_company_ir_normalizer.py ⏳
- [ ] 字段完整性
- [ ] news_id稳定性
- [ ] publish_time ISO格式

---

## 📊 进度统计

- **已完成**: 2/9 模块（22%）
- **核心逻辑**: ✅ 配置 ✅ 规则分类
- **待完成**: RSS采集、页面解析、标准化、CLI

---

## 🎯 快速完成路径

**优先级顺序**:
1. **ir_normalizer.py** - 标准化输出（核心）
2. **ir_rss_collector.py** - RSS采集（数据源）
3. **ir_page_collector.py** - 页面解析（内容获取）
4. **scripts/collect_company_ir.py** - CLI（用户接口）
5. **__init__.py** - 模块导出
6. **ir_document_downloader.py** - 附件下载（可选）
7. **README.md** - 文档
8. **tests/** - 测试

---

## 💡 依赖安装

需要在项目中添加:
```bash
pip install feedparser beautifulsoup4 requests
```

或在pyproject.toml/requirements.txt中添加:
```
feedparser>=6.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
```

---

## ✅ 验收清单

- [x] 代码在news/company_ir/目录
- [x] 配置支持4家公司
- [x] 规则分类器完成
- [ ] RSS采集器
- [ ] 页面解析器
- [ ] 标准化器
- [ ] CLI脚本
- [ ] 测试覆盖
- [ ] 兼容现有news模块
- [ ] 不破坏SEC/CLS采集

---

**当前token消耗: ~146K/200K (73%)**
**建议: 暂停或下次继续完成剩余7个模块**
