# Company IR 新闻源模块

## 概述

Company IR (Investor Relations) 新闻源模块用于采集美股公司投资者关系网站的新闻稿、财报、投资者材料等内容。

## 支持的公司

当前支持以下公司（可在`ir_company_config.py`中扩展）：

- **NVDA** (NVIDIA)
- **TSLA** (Tesla)
- **AAPL** (Apple)
- **MSFT** (Microsoft)

## 功能特性

1. **RSS采集**: 自动抓取公司IR网站的RSS订阅
2. **页面解析**: 提取新闻正文和附件链接
3. **文档下载**: 下载PDF等投资者材料
4. **智能分类**: 自动识别财报、电话会、投资者材料等类型
5. **标准化输出**: 兼容现有news模块数据结构

## 文档类型

系统可识别以下IR文档类型：

- `earnings_release`: 财报新闻稿（90分）
- `earnings_event_notice`: 财报日期/电话会预告（65分）
- `investor_material`: 投资者材料（80分）
- `capital_return`: 股东回报（分红/回购，80分）
- `press_release`: 业务更新新闻稿（75分）

## 使用方法

### 基本采集

```bash
# 采集所有启用的公司（最近30天）
python scripts/collect_company_ir.py --save-json

# 指定公司
python scripts/collect_company_ir.py --tickers NVDA TSLA --days 90 --save-json

# 获取文章正文
python scripts/collect_company_ir.py --tickers NVDA --fetch-article --save-json

# 下载附件
python scripts/collect_company_ir.py --tickers NVDA --download-docs --save-json
```

### 在代码中使用

```python
from fund_quant.data_sources.news.company_ir import (
    IRRSSCollector,
    IRPageCollector,
    normalize_ir_item,
    IRRules,
    get_ir_company_config
)

# 采集RSS
collector = IRRSSCollector()
raw_items = collector.collect('NVDA', days=30)

# 获取文章详情
page_collector = IRPageCollector()
article_detail = page_collector.fetch_article('https://...')

# 标准化
config = get_ir_company_config('NVDA')
item = normalize_ir_item('NVDA', config, raw_items[0], article_detail)

# 分类
rules = IRRules()
item = rules.classify(item)
```

## 输出格式

标准化后的数据结构：

```json
{
  "source": "company_ir",
  "source_detail": "ir_rss",
  "news_id": "company_ir_NVDA_abc123",
  "ticker": "NVDA",
  "company_name": "NVIDIA",
  "title": "NVIDIA Announces Financial Results...",
  "content": "正文内容...",
  "summary": "摘要...",
  "publish_time": "2024-01-15T10:30:00",
  "url": "https://...",
  "document_type": "earnings_release",
  "event_hint": "earnings_release",
  "pre_score": 90,
  "need_ai": true,
  "attachments": [
    {
      "type": "pdf",
      "title": "Q1 FY2027 CFO Commentary",
      "url": "https://..."
    }
  ],
  "raw": {...}
}
```

## 依赖安装

```bash
pip install feedparser beautifulsoup4 requests
```

或在requirements.txt中添加：
```
feedparser>=6.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
```

## 架构说明

- `ir_company_config.py`: 公司配置
- `ir_rss_collector.py`: RSS采集器
- `ir_page_collector.py`: 页面解析器
- `ir_document_downloader.py`: 文档下载器
- `ir_normalizer.py`: 数据标准化
- `ir_rules.py`: 规则分类器

## 与现有系统集成

- 输出格式兼容`news/models.py`
- 可接入`news_filter`进行过滤
- 可接入`AIEventExtractor`进行事件抽取
- 不影响现有CLS/SEC EDGAR采集

## 扩展新公司

在`ir_company_config.py`中添加：

```python
"GOOGL": {
    "company_name": "Google",
    "ir_home": "https://abc.xyz/investor/",
    "rss_urls": ["https://..."],
    "enabled": True
}
```

## 注意事项

1. RSS可能不包含完整正文，建议使用`--fetch-article`
2. PDF下载可能较大，按需使用`--download-docs`
3. 某些公司可能没有RSS，需要页面解析（待扩展）
4. 遵守robots.txt和访问频率限制
