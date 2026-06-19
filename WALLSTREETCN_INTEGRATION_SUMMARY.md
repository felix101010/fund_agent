# 华尔街见闻新闻源集成 - 实施总结

**日期**: 2026-06-17  
**状态**: ✅ 完成

## 修改的文件列表

### 1. 修改文件（3个）

#### `src/fund_quant/data_sources/news/models.py`
**修改内容**:
- 在 `RawNews` dataclass 中添加 `source_role` 字段
- 类型：`Optional[str] = None`
- 用途：区分新闻角色（announcement/market_context/industry_news）
- 同步更新 `to_dict()` 方法

#### `src/fund_quant/data_sources/news/news_service.py`
**修改内容**:
- 重命名 `self.collector` 为 `self.cls_collector`
- 新增 `self.wscn_collector = WallstreetcnCollector()`
- 新增方法 `fetch_latest(source, limit)` - 按来源抓取
- 新增方法 `fetch_all_latest(limit_per_source)` - 抓取所有来源
- 保持 `fetch_and_store()` 向后兼容
- 添加错误处理，单个源失败不影响其他源

#### `src/fund_quant/nlp/news_filter/keyword_rules.py`
**修改内容**:
- 新增 `WALLSTREETCN_HIGH_VALUE_KEYWORDS` 列表（33个关键词）
- 新增 `WALLSTREETCN_LOW_VALUE_KEYWORDS` 列表（7个关键词）
- 更新 `__all__` 导出列表

### 2. 新增文件（2个）

#### `src/fund_quant/data_sources/news/wallstreetcn_collector.py`
**功能**:
- 华尔街见闻新闻采集器（RSS版本）
- 使用 feedparser 解析 RSS
- 支持自定义 RSS URL
- 默认地址：`http://127.0.0.1:1201/wallstreetcn/live/global/1`
- 生成稳定的 news_id：`wscn_xxxxxxxxxxxxxxxx`
- 自动清洗HTML标签和空白字符
- 智能解析发布时间
- 返回 `List[RawNews]`

#### `scripts/test_wallstreetcn.py`
**功能**:
- 测试脚本，支持两种模式
- 基础模式：测试采集器单独运行
- 集成模式：测试 NewsService 集成

## 最终目录结构

```
src/fund_quant/data_sources/news/
├── __init__.py
├── cls_api_collector.py          # 财联社采集器
├── wallstreetcn_collector.py     # 华尔街见闻采集器（新增）
├── deduplicator.py                # 去重工具
├── models.py                      # 数据模型（已修改）
├── news_service.py                # 新闻服务（已修改）
└── company_ir/

src/fund_quant/nlp/news_filter/
├── keyword_rules.py               # 关键词规则（已修改）
└── ...

scripts/
├── test_wallstreetcn.py           # 测试脚本（新增）
└── ...
```

## 华尔街见闻定位

### source 信息
- **source**: `wallstreetcn`
- **source_role**: `market_context`

### 覆盖范围
- 美联储政策（降息/加息/点阵图）
- 宏观数据（CPI/PCE/非农/初请失业金/零售销售）
- 市场指标（美债收益率/美元/VIX）
- 大宗商品（黄金/原油/OPEC/EIA/API）
- 美股指数（纳指/标普/道指）
- 科技巨头（英伟达/特斯拉/苹果/微软/Meta/谷歌）
- 半导体（台积电/ASML/美光/博通/AMD）
- AI产业（算力/芯片/数据中心）
- 中概股/港股科技

## 使用方法

### 1. 启动 RSSHub（前置条件）

```bash
# Docker 方式
docker run -d --name rsshub -p 1201:1200 diygod/rsshub

# 验证
curl http://127.0.0.1:1201/wallstreetcn/live/global/1
```

### 2. 测试采集器

```bash
# 基础测试（测试采集器）
python scripts/test_wallstreetcn.py

# 集成测试（测试 NewsService）
python scripts/test_wallstreetcn.py --integration
```

### 3. 在代码中使用

#### 方式 A：直接使用采集器

```python
from fund_quant.data_sources.news.wallstreetcn_collector import WallstreetcnCollector

# 创建采集器
collector = WallstreetcnCollector()

# 抓取新闻
news_list = collector.fetch_latest(limit=20)

# 自定义 RSS URL
collector = WallstreetcnCollector(rss_url="http://127.0.0.1:1201/wallstreetcn/live/global/2")
news_list = collector.fetch_latest(limit=30)
```

#### 方式 B：通过 NewsService

```python
from fund_quant.data_sources.news.news_service import NewsService

service = NewsService()

# 只抓取华尔街见闻
wscn_df = service.fetch_latest("wallstreetcn", limit=20)

# 只抓取财联社（兼容原有代码）
cls_df = service.fetch_latest("cls", limit=20)

# 抓取所有来源
all_df = service.fetch_all_latest(limit_per_source=20)
```

### 4. 预期输出格式

```
================================================================================
新闻 1/20
================================================================================
来源: wallstreetcn
角色: market_context
ID: wscn_3712345
标题: 美国5月零售销售环比增长0.9%，高于预期
时间: 2026-06-17 20:30:00
URL: https://wallstreetcn.com/articles/3712345
正文摘要: 美国商务部数据显示...
采集延迟: 45秒
```

## 关键词规则

### 高价值关键词（33个）
已添加到 `WALLSTREETCN_HIGH_VALUE_KEYWORDS`：
- 美联储相关：美联储、鲍威尔、降息、加息、利率决议、点阵图
- 宏观数据：CPI、PCE、非农、初请失业金、零售销售、PMI
- 市场指标：美元、美债、收益率、10年期美债、2年期美债
- 大宗商品：黄金、原油、OPEC、EIA、API
- 美股指数：纳指、标普、道指、VIX、恐慌指数
- 科技公司：英伟达、特斯拉、苹果、微软、Meta、谷歌
- 半导体：台积电、ASML、美光、博通、AMD
- AI产业：半导体、AI、算力、芯片、服务器、数据中心
- 中国市场：港股科技、中概股、人民币汇率

### 低价值关键词（7个）
已添加到 `WALLSTREETCN_LOW_VALUE_KEYWORDS`：
- 直播、专栏、会员、广告、活动、课程、招聘

## 去重逻辑

### 现有去重策略（保持不变）
1. 按 `news_id` 去重（同源内去重）
2. 按 `title + publish_time` 去重（跨源去重）

### news_id 生成规则
```python
# 优先级1：从链接提取ID
wscn_3712345  # 来自 https://wallstreetcn.com/articles/3712345

# 优先级2：链接hash
wscn_a1b2c3d4e5f67890  # MD5(link)[:16]

# 优先级3：标题+时间hash
wscn_f9e8d7c6b5a43210  # MD5(title_time)[:16]
```

## 错误处理

### 1. RSSHub 未启动
```
✗ 华尔街见闻采集失败: ...
请确认 RSSHub 正在运行，默认地址: http://127.0.0.1:1200
```

### 2. RSS 解析失败
```
RSS解析失败: ...
请确认 RSSHub 正在运行，默认地址: http://127.0.0.1:1200
```

### 3. 单源失败不影响其他源
```
✓ 财联社: 20 条
✗ 华尔街见闻采集失败: Connection refused
✓ 合并后总计: 20 条
```

## 后续集成建议

### 1. Pipeline 集成
华尔街见闻新闻采集后，会走现有的处理流程：
```
采集 → 标准化 → 去重 → 规则过滤 → AI抽取 → 题材标准化 → 保存
```

### 2. 规则过滤增强
可以在 `rule_filter.py` 中根据 `source` 字段应用不同规则：

```python
if source == "wallstreetcn":
    # 华尔街见闻规则
    if any(kw in text for kw in WALLSTREETCN_HIGH_VALUE_KEYWORDS):
        action = "analyze"  # 送AI
    elif any(kw in text for kw in WALLSTREETCN_LOW_VALUE_KEYWORDS):
        action = "archive"  # 丢弃
    else:
        action = "context"  # 保留但不送AI
```

### 3. action 类型建议
- `archive`: 低价值，丢弃
- `context`: 有市场背景价值，但不送AI
- `analyze`: 高价值，送AI分析
- `risk_review`: 地缘/黑天鹅/政策风险

### 4. 数据库表结构
如需存储 `source_role`，请在 ClickHouse 中添加字段：

```sql
ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS source_role Nullable(String);
```

## 测试验收

### 基础测试
```bash
python scripts/test_wallstreetcn.py
```

预期：
- ✅ 成功连接 RSSHub
- ✅ 解析 RSS feed
- ✅ 提取 20 条新闻
- ✅ 生成稳定 news_id
- ✅ 清洗 HTML 标签
- ✅ 解析发布时间
- ✅ 打印格式化输出

### 集成测试
```bash
python scripts/test_wallstreetcn.py --integration
```

预期：
- ✅ NewsService 可以单独抓取华尔街见闻
- ✅ NewsService 可以单独抓取财联社（向后兼容）
- ✅ NewsService 可以同时抓取两个源
- ✅ 单源失败不影响其他源
- ✅ 正确合并多源数据

## 依赖检查

```bash
# 检查 feedparser 是否已安装
python -c "import feedparser; print(feedparser.__version__)"

# 检查 dateutil 是否已安装
python -c "import dateutil; print(dateutil.__version__)"
```

如果缺少依赖：
```bash
uv pip install feedparser python-dateutil
```

## 核心设计原则

1. ✅ **最小改动** - 只修改3个文件，新增2个文件
2. ✅ **向后兼容** - 保持原有财联社逻辑不变
3. ✅ **错误隔离** - 单源失败不影响整体
4. ✅ **清晰错误** - 提示RSSHub启动状态
5. ✅ **职责分离** - collector只负责采集，不做AI处理
6. ✅ **代码复用** - 复用现有models、deduplicator、service
7. ✅ **扩展性** - 支持自定义RSS URL和多category

完成！🚀
