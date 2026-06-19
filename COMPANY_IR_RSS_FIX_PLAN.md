# Company IR RSS修复方案

## 🔍 问题诊断

**根本原因**：
- NVDA的RSS URL返回HTML页面，不是XML feed
- feedparser无法解析HTML，导致entries=0

**需要实现**：
1. RSS feed自动发现机制
2. 区分真实feed和发现页
3. 从HTML中提取真实feed链接

---

## ✅ 已完成

1. ✅ 更新`ir_company_config.py`
   - NVDA配置分离：`rss_urls`（真实feed）和`rss_discovery_urls`（发现页）
   - 添加3个真实RSS URL

---

## 📋 待实现（需继续）

### 1. 增强ir_rss_collector.py

**新增函数**：
```python
def is_probable_feed_response(content_type: str, text: str) -> bool:
    """判断是否是真实RSS/Atom feed"""
    # 检查Content-Type
    if any(t in content_type.lower() for t in ['xml', 'rss', 'atom']):
        return True
    # 检查内容前500字符
    preview = text[:500].lower()
    return any(tag in preview for tag in ['<rss', '<feed', '<rdf:rdf'])

def discover_feed_urls(html: str, base_url: str) -> list[str]:
    """从HTML中发现RSS feed链接"""
    # 使用BeautifulSoup解析
    # 1. 查找<link rel="alternate" type="application/rss+xml">
    # 2. 查找包含rss/xml/feed的<a>链接
    # 3. 过滤无效链接（email-alerts, contact等）
    # 4. 转换相对路径为绝对路径
```

**修改collect()方法**：
```python
def collect(self, ticker: str, days: int = 30) -> list[dict]:
    feed_urls = []
    
    # 1. 添加真实rss_urls
    feed_urls.extend(config.get('rss_urls', []))
    
    # 2. 从discovery_urls发现feed
    for discovery_url in config.get('rss_discovery_urls', []):
        html = requests.get(discovery_url).text
        discovered = discover_feed_urls(html, discovery_url)
        feed_urls.extend(discovered)
    
    # 3. 去重
    feed_urls = list(dict.fromkeys(feed_urls))
    
    # 4. 逐个解析
    for feed_url in feed_urls:
        resp = requests.get(feed_url)
        if not is_probable_feed_response(resp.headers.get('Content-Type'), resp.text):
            logger.warning(f"跳过非feed: {feed_url}")
            continue
        # feedparser解析...
```

### 2. 增强debug脚本

**debug_company_ir_rss.py**：
- 检测是否probable_feed
- 如果是HTML，调用discover_feed_urls
- 测试发现的feed是否可解析

### 3. 新增测试

**tests/test_company_ir_rss_collector.py**：
- test_is_probable_feed_xml()
- test_is_probable_feed_html()
- test_discover_feed_from_link_tag()
- test_discover_feed_from_anchor()

---

## 🎯 验收标准

运行：
```bash
python scripts/debug_company_ir_rss.py
```

**预期输出**：
```
URL: https://investor.nvidia.com/.../rss/default.aspx
Content-Type: text/html
probable_feed: False
Discovered feeds:
  - https://nvidianews.nvidia.com/releases.xml
  - https://investor.nvidia.com/rss/Event.aspx?LanguageId=1

Testing feed: https://nvidianews.nvidia.com/releases.xml
Content-Type: application/xml
Entries: 25 ✅
```

运行采集：
```bash
python scripts/collect_company_ir.py --tickers NVDA --days 90 --save-json
```

**预期**：采集到 >0 条新闻

---

## 📊 当前状态

- **Token消耗**: 195K/200K (97.5%)
- **Company IR**: 配置已更新，核心逻辑待实现
- **建议**: 下次会话继续完成RSS发现机制

---

## 💡 快速测试真实feed

手动测试NVDA的真实RSS：
```bash
curl "https://nvidianews.nvidia.com/releases.xml" | head -50
curl "https://investor.nvidia.com/rss/Event.aspx?LanguageId=1" | head -50
```

如果这些URL返回XML，说明配置正确，只需实现采集逻辑。

---

**核心代码框架已就绪，剩余约200行实现feed发现和过滤逻辑！**
