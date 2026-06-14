# SEC EDGAR 采集模块完整架构说明

## 一、整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SEC EDGAR 采集模块                             │
│                    (遵守SEC Fair Access规则)                         │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
        ┌───────────▼────┐  ┌──────▼─────┐  ┌───▼──────────┐
        │  配置层         │  │  映射层     │  │  客户端层     │
        │  sec_config    │  │ticker_mapper│  │  sec_client  │
        └───────────────┘  └────────────┘  └──────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
        ┌───────────▼────┐  ┌──────▼─────┐  ┌───▼──────────┐
        │  采集层         │  │  下载层     │  │  标准化层     │
        │filing_collector│  │filing_down. │  │filing_normal.│
        └────────────────┘  └────────────┘  └──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
        ┌───────────▼────────┐      ┌────────────▼─────────┐
        │  命令行脚本层        │      │  测试层               │
        │collect_sec_filings │      │test_sec_edgar_collect│
        └────────────────────┘      └──────────────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │          对接现有新闻事件系统                    │
        │  raw_news → 规则过滤 → AI抽取 → 评分 → 入库    │
        └──────────────────────────────────────────────┘
```

---

## 二、模块层次详解

### 第0层：配置层（Foundation Layer）

**文件**: `sec_config.py`

**职责**: 定义全局配置和规则

**核心配置**:
```python
# SEC Fair Access规则
SEC_REQUEST_RATE = 2  # 每秒2个请求（安全范围1-3）
SEC_MAX_RATE = 10     # SEC规定的绝对上限

# User-Agent（必须含邮箱）
SEC_USER_AGENT = "fund_quant_system/0.1 (contact: your_email@example.com)"

# SEC数据源URL
SEC_DATA_URL = "https://data.sec.gov"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

# 表单类型定义
FORM_TYPES = {
    "8-K": {"description": "Current Report", "priority": "high"},
    "10-Q": {"description": "Quarterly Report", "priority": "medium"},
    "10-K": {"description": "Annual Report", "priority": "medium"}
}

# 高价值关键词（8-K）
HIGH_VALUE_KEYWORDS = [
    "earnings", "guidance", "merger", "acquisition",
    "CEO", "CFO", "bankruptcy", "dividend", "FDA"
]

# 重点股票池
DEFAULT_TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", ...]

# 内容截断配置
CONTENT_MIN_LENGTH = 100     # 最小有效长度
CONTENT_MAX_LENGTH = 30000   # 最大长度（传给AI）
```

**设计理念**: 集中配置，便于调整限流、股票池、关键词

---

### 第1层：基础服务层（Infrastructure Layer）

#### 1.1 Ticker映射器

**文件**: `ticker_mapper.py`

**职责**: Ticker ↔ CIK 双向映射

**数据源**: SEC官方 `company_tickers.json`
```
https://www.sec.gov/files/company_tickers.json
```

**核心方法**:
```python
class TickerMapper:
    def get_cik(ticker: str) -> str:
        """NVDA → 0001045810（10位CIK）"""
    
    def get_ticker(cik: str) -> str:
        """0001045810 → NVDA"""
    
    @staticmethod
    def pad_cik(cik: str) -> str:
        """1045810 → 0001045810（补齐10位）"""
    
    @staticmethod
    def remove_cik_leading_zeros(cik: str) -> str:
        """0001045810 → 1045810（用于拼接URL）"""
```

**缓存机制**:
```
data/cache/sec_ticker_cik_map.json
```
首次从SEC下载，后续使用本地缓存。

**映射关系示例**:
```json
{
  "ticker_to_cik": {
    "NVDA": "0001045810",
    "AAPL": "0000320193",
    "TSLA": "0001318605"
  },
  "cik_to_ticker": {
    "0001045810": "NVDA",
    "0000320193": "AAPL"
  }
}
```

---

#### 1.2 SEC客户端

**文件**: `sec_client.py`

**职责**: 
- 统一HTTP请求
- 请求限流（遵守Fair Access）
- 错误处理

**核心机制**:
```python
class SECClient:
    def __init__(self, rate_limit=2):
        self.rate_limit = 2  # 每秒2个请求
        self.min_interval = 1.0 / 2  # 最小间隔0.5秒
        self.last_request_time = 0
        self.headers = {'User-Agent': SEC_USER_AGENT}
    
    def _wait_for_rate_limit(self):
        """自动等待，确保请求间隔"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
    def get_submissions(self, cik: str) -> dict:
        """获取公司submissions JSON"""
        self._wait_for_rate_limit()  # 自动限流
        url = f"{SEC_DATA_URL}/submissions/CIK{cik}.json"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def download_filing(self, url: str) -> str:
        """下载filing正文"""
        self._wait_for_rate_limit()  # 自动限流
        response = requests.get(url, headers=self.headers)
        return response.text
```

**限流示意图**:
```
请求1 → [等待0.5s] → 请求2 → [等待0.5s] → 请求3
时间: 0s         0.5s         1.0s         1.5s
速率: 2 req/s（符合SEC规则）
```

---

### 第2层：业务逻辑层（Business Logic Layer）

#### 2.1 Filing采集器

**文件**: `filing_collector.py`

**职责**: 
- 获取submissions JSON
- 筛选表单类型
- 日期过滤
- 生成filing_id和URL

**数据模型**:
```python
@dataclass
class FilingMetadata:
    filing_id: str              # sec_NVDA_0001045810-24-000123
    ticker: str                 # NVDA
    cik: str                    # 0001045810（10位）
    company_name: str           # NVIDIA CORP
    form_type: str              # 8-K
    accession_number: str       # 0001045810-24-000123（原始格式）
    filing_date: str            # 2024-12-31
    report_date: str            # 2024-12-31
    acceptance_datetime: str    # 2024-12-31T16:30:00.000Z
    primary_document: str       # nvda-20241231.htm
    filing_url: str             # https://www.sec.gov/Archives/...
    is_new: bool                # 是否新filing
```

**工作流程**:
```python
def collect_filings(tickers, forms, since_date, days):
    all_filings = []
    
    for ticker in tickers:
        # 1. Ticker → CIK
        cik = TickerMapper.get_cik(ticker)
        
        # 2. 获取submissions JSON
        submissions = SECClient.get_submissions(cik)
        
        # 3. 解析filings
        recent = submissions['filings']['recent']
        accession_numbers = recent['accessionNumber']
        form_types = recent['form']
        filing_dates = recent['filingDate']
        
        # 4. 筛选和过滤
        for i in range(len(accession_numbers)):
            # 过滤表单类型
            if form_types[i] not in forms:
                continue
            
            # 过滤日期
            if filing_dates[i] < since_date:
                continue
            
            # 5. 生成filing_id
            filing_id = f"sec_{ticker}_{accession_numbers[i]}"
            
            # 6. 构建filing_url
            filing_url = _build_filing_url(cik, accession, doc)
            
            # 7. 创建FilingMetadata
            filing = FilingMetadata(...)
            all_filings.append(filing)
    
    return all_filings
```

**URL拼接规则**:
```python
# 输入
cik = "0001045810"
accession = "0001045810-24-000123"
doc = "nvda-20241231.htm"

# 处理
cik_no_zeros = "1045810"           # 移除前导零
accession_no_dash = "000104581024000123"  # 移除横线

# 输出
url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_no_dash}/{doc}"
# https://www.sec.gov/Archives/edgar/data/1045810/000104581024000123/nvda-20241231.htm
```

---

#### 2.2 Filing下载器

**文件**: `filing_downloader.py`

**职责**: 
- 下载filing正文
- HTML转纯文本
- 清洗和截断

**核心流程**:
```python
class FilingDownloader:
    def download_and_parse(self, filing_url: str) -> str:
        # 1. 下载
        raw_html = SECClient.download_filing(filing_url)
        
        # 2. 清洗HTML
        text = self._clean_html(raw_html)
        
        # 3. 检查最小长度
        if len(text) < 100:
            return None  # 内容过短，视为无效
        
        # 4. 截断
        text = self._truncate_content(text, max_length=30000)
        
        return text
```

**HTML清洗步骤**:
```python
def _clean_html(self, html_content: str) -> str:
    # 1. BeautifulSoup解析
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 2. 移除无用标签
    for tag in soup(['script', 'style', 'meta', 'link']):
        tag.decompose()
    
    # 3. 提取文本
    text = soup.get_text(separator=' ', strip=True)
    
    # 4. 清理空白字符
    text = re.sub(r'\s+', ' ', text)  # 多个空格→单个空格
    text = text.strip()
    
    return text
```

**清洗效果示例**:
```html
<!-- 输入HTML -->
<html>
<head><style>.header{color:red}</style></head>
<body>
    <h1>Item 1.01   Entry into Material Agreement</h1>
    <p>The Company entered into a   definitive agreement.</p>
    <script>alert('test');</script>
</body>
</html>

<!-- 输出纯文本 -->
Item 1.01 Entry into Material Agreement The Company entered into a definitive agreement.
```

---

#### 2.3 Filing标准化器

**文件**: `filing_normalizer.py`

**职责**: 
- 转换为系统统一格式
- 对接现有新闻事件系统

**标准化流程**:
```python
class FilingNormalizer:
    @staticmethod
    def normalize(filing: FilingMetadata, content: str) -> dict:
        return {
            # 必填字段（兼容NewsItem）
            "source": "sec_edgar",
            "news_id": "sec_NVDA_0001045810-24-000123",
            "title": "NVDA 8-K 2024-12-31 - NVIDIA CORP",
            "content": "清洗后的纯文本...",
            "publish_time": datetime(2024, 12, 31, 16, 30),
            "url": "https://www.sec.gov/Archives/...",
            
            # SEC特有字段
            "ticker": "NVDA",
            "cik": "0001045810",
            "company_name": "NVIDIA CORP",
            "form_type": "8-K",
            "accession_number": "0001045810-24-000123",
            "filing_date": "2024-12-31",
            "report_date": "2024-12-31"
        }
```

**对接方式**:
```python
# 方案A：复用raw_news表
def to_raw_news_format(filing, content):
    return {
        "news_id": "sec_NVDA_0001045810-24-000123",
        "source": "sec_edgar",
        "title": "NVDA 8-K 2024-12-31 - NVIDIA CORP",
        "content": content,
        "publish_time": filing_date,
        "url": filing_url,
        "raw_data": json.dumps({
            "ticker": "NVDA",
            "cik": "0001045810",
            "form_type": "8-K"
        })
    }

# 方案B：新建raw_filings表（推荐）
CREATE TABLE raw_filings (
    filing_id String,
    source String,
    ticker String,
    cik String,
    company_name String,
    form_type String,
    accession_number String,
    filing_date Date,
    filing_url String,
    content String,
    created_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (ticker, form_type, filing_date);
```

---

### 第3层：应用层（Application Layer）

#### 3.1 命令行脚本

**文件**: `collect_sec_filings.py`

**职责**: 
- 命令行接口
- 流程编排
- 结果展示

**完整流程**:
```python
def main():
    # 1. 解析参数
    args = parse_args()
    tickers = args.tickers or DEFAULT_TICKERS
    
    # 2. 初始化组件
    collector = FilingCollector()
    downloader = FilingDownloader()
    normalizer = FilingNormalizer()
    
    # 3. 采集元数据
    print("📥 采集filings元数据...")
    filings = collector.collect_filings(
        tickers=tickers,
        forms=['8-K'],
        days=7
    )
    
    # 4. 下载正文
    print("📥 下载filing正文...")
    for filing in filings:
        content = downloader.download_and_parse(filing.filing_url)
        
        # 5. 标准化
        normalized = normalizer.normalize(filing, content)
        
        # 6. 打印/保存
        print_filing(filing, content)
        results.append(normalized)
    
    # 7. 保存JSON
    if args.save_json:
        save_results(results, args.output_dir)
    
    # 8. 打印汇总
    print_summary(results)
```

**命令示例**:
```bash
# 基础用法
python scripts/collect_sec_filings.py --tickers NVDA --forms 8-K --days 7

# 多ticker + 保存JSON
python scripts/collect_sec_filings.py \
    --tickers NVDA TSLA AAPL \
    --forms 8-K 10-Q \
    --days 30 \
    --save-json \
    --output-dir output/sec_edgar
```

---

### 第4层：测试层（Testing Layer）

**文件**: `test_sec_edgar_collector.py`

**测试用例**:
```python
# 1. CIK补齐测试
def test_pad_cik_10_digits():
    assert TickerMapper.pad_cik("1045810") == "0001045810"

# 2. URL拼接测试
def test_build_archives_url():
    url = collector._build_filing_url(
        "0001045810",
        "0001045810-24-000123",
        "nvda.htm"
    )
    assert "1045810" in url
    assert "000104581024000123" in url

# 3. HTML清洗测试
def test_html_to_text():
    html = "<html><body><p>Test</p><script>alert()</script></body></html>"
    text = downloader._clean_html(html)
    assert "Test" in text
    assert "alert" not in text

# 4. 表单筛选测试
def test_filter_8k_forms():
    forms = ["8-K", "10-Q", "8-K/A"]
    filtered = [f for f in forms if f in ["8-K", "8-K/A"]]
    assert len(filtered) == 2
```

---

## 三、数据流图

```
1. 用户输入
   ├─ tickers: ["NVDA", "TSLA"]
   ├─ forms: ["8-K"]
   └─ days: 7

2. Ticker映射
   NVDA → 0001045810
   TSLA → 0001318605

3. 获取Submissions
   GET https://data.sec.gov/submissions/CIK0001045810.json
   │
   └─ 返回JSON:
      {
        "cik": "0001045810",
        "name": "NVIDIA CORP",
        "filings": {
          "recent": {
            "accessionNumber": ["0001045810-24-000123", ...],
            "form": ["8-K", "10-Q", ...],
            "filingDate": ["2024-12-31", ...],
            "primaryDocument": ["nvda.htm", ...]
          }
        }
      }

4. 筛选Filings
   过滤: form=="8-K" AND filingDate >= "2024-06-07"
   │
   └─ 结果: 3个8-K filings

5. 下载正文
   对每个filing:
   GET https://www.sec.gov/Archives/edgar/data/1045810/000104581024000123/nvda.htm
   │
   └─ 返回HTML正文

6. 清洗HTML
   HTML → BeautifulSoup → 移除<script><style> → 提取文本 → 清理空白

7. 截断内容
   如果 len(text) > 30000:
       text = text[:30000] + "[Content truncated]"

8. 标准化格式
   FilingMetadata + content → 统一事件格式
   │
   └─ {
        "source": "sec_edgar",
        "news_id": "sec_NVDA_0001045810-24-000123",
        "title": "NVDA 8-K 2024-12-31",
        "content": "清洗后的纯文本",
        "ticker": "NVDA",
        "form_type": "8-K"
      }

9. 对接现有系统
   ├─ 写入raw_news或raw_filings表
   ├─ 进入规则过滤（SimpleRuleFilter）
   ├─ need_ai=True → AI事件抽取（AIEventExtractor）
   ├─ 主题标准化（ThemeNormalizer）
   ├─ 评分（EventScorer）
   └─ 最终输出事件结果
```

---

## 四、关键设计决策

### 4.1 为什么要限流？

**SEC Fair Access规则**:
- 超过10 req/s会被拉黑
- 必须设置User-Agent含邮箱
- 否则返回403 Forbidden

**实现方式**:
```python
# 每次请求前自动等待
def _wait_for_rate_limit(self):
    elapsed = time.time() - self.last_request_time
    if elapsed < 0.5:  # 2 req/s = 0.5s间隔
        time.sleep(0.5 - elapsed)
```

### 4.2 为什么要CIK补齐10位？

**SEC API要求**:
```
正确: https://data.sec.gov/submissions/CIK0001045810.json ✅
错误: https://data.sec.gov/submissions/CIK1045810.json ❌（404）
```

但Archives URL要移除前导零:
```
正确: https://www.sec.gov/Archives/edgar/data/1045810/... ✅
错误: https://www.sec.gov/Archives/edgar/data/0001045810/... ❌（404）
```

### 4.3 为什么要HTML清洗？

**原始HTML问题**:
- 包含<script>、<style>等无用标签
- 大量HTML标签和属性
- 空白字符混乱
- 不适合传给AI

**清洗后优点**:
- 纯文本，易于AI理解
- 体积减小70-80%
- 去除噪音，聚焦内容

### 4.4 为什么要内容截断？

**原因**:
- 8-K平均长度：5K-50K字符
- 10-K可能超过500K字符
- AI有上下文长度限制
- 超长内容影响处理速度和成本

**截断策略**:
- 最小100字符（低于视为无效）
- 最大30000字符（足够AI提取关键信息）
- 截断后添加提示标记

---

## 五、与现有系统的集成

### 5.1 数据入口

```python
# SEC Filing → 统一格式
normalized = FilingNormalizer.normalize(filing, content)

# 转为NewsItem
news_item = NewsItem(
    news_id=normalized['news_id'],
    source=normalized['source'],
    title=normalized['title'],
    content=normalized['content'],
    publish_time=normalized['publish_time']
)
```

### 5.2 规则过滤

```python
# 8-K默认高优先级
from fund_quant.nlp.news_filter import SimpleRuleFilter

filter_result = SimpleRuleFilter().filter(news_item)

# 建议规则：
if form_type == "8-K":
    action = "analyze"
    need_ai = True
```

### 5.3 AI抽取

```python
from fund_quant.nlp.news_ai import AIEventExtractor

if filter_result.need_ai:
    event_result = AIEventExtractor().extract(news_item, filter_result)
```

### 5.4 主题标准化

```python
from fund_quant.nlp.theme_mapping import ThemeNormalizer

theme_result = ThemeNormalizer().normalize(event_result)
# 美股事件可能映射到：
# - NVDA财报 → ai_compute主题
# - TSLA重组 → new_energy_vehicle主题
```

### 5.5 评分

```python
from fund_quant.nlp.scoring import EventScorer

score_result = EventScorer().calculate_score(event_result)
# trade_priority: urgent/high/candidate/watch
```

---

## 六、目录结构总览

```
fund_agent/
├── src/fund_quant/data_sources/sec_edgar/
│   ├── __init__.py                    # 模块导出
│   ├── sec_config.py                  # 配置层（限流、关键词、股票池）
│   ├── ticker_mapper.py               # 映射层（Ticker↔CIK）
│   ├── sec_client.py                  # 客户端层（HTTP请求+限流）
│   ├── filing_collector.py            # 采集层（筛选filings）
│   ├── filing_downloader.py           # 下载层（HTML清洗）
│   ├── filing_normalizer.py           # 标准化层（转统一格式）
│   └── README.md                      # 完整文档
│
├── scripts/
│   └── collect_sec_filings.py         # 命令行脚本
│
├── tests/
│   └── test_sec_edgar_collector.py    # 单元测试
│
└── data/
    ├── cache/
    │   └── sec_ticker_cik_map.json    # Ticker映射缓存
    └── review/sec_filings/
        └── sec_filings_*.json         # 采集结果
```

---

## 七、关键指标和性能

**限流性能**:
- 请求频率：2 req/s
- 单个ticker：~0.5秒（获取submissions）
- 下载filing：~1秒/个
- 10个ticker，平均每个3个8-K：~35秒

**数据量**:
- Ticker映射：~10K公司
- 单个8-K：5K-50K字符
- 截断后：最多30K字符
- JSON输出：~20-100KB/filing

**可靠性**:
- 自动限流：遵守SEC规则
- 错误重试：单个失败不影响批次
- HTML清洗：双重策略（BeautifulSoup + 正则）
- 内容验证：最小长度检查

---

## 八、后续扩展方向

1. **更多表单类型**:
   - 10-Q/10-K财报分析
   - Form 4内部交易追踪
   - 13F机构持仓变化
   - S-1 IPO监控

2. **智能解析**:
   - 8-K Item类型识别（Item 1.01并购、Item 2.02财报）
   - 10-K关键指标提取（营收、利润、指引）
   - Form 4交易类型分类（买入/卖出/期权）

3. **数据库优化**:
   - 新建raw_filings表
   - 去重索引
   - 分区存储
   - 历史数据回填

4. **实时监控**:
   - Daemon模式持续采集
   - 新filing推送通知
   - 关键事件告警

这就是SEC EDGAR采集模块的完整架构！有什么问题随时问我 🚀
