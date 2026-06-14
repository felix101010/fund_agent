# SEC EDGAR 采集模块

从SEC EDGAR获取美股公司filings（8-K/10-Q/10-K等），对接现有新闻事件系统。

## 特性

✅ **遵守SEC Fair Access规则**
- 请求频率默认2 req/s，不超过10 req/s
- 必须设置User-Agent（含邮箱）
- 自动限流

✅ **支持多种表单类型**
- 8-K（重大事件）- 优先级最高
- 10-Q（季报）
- 10-K（年报）
- Form 4（内部交易）
- S-1（IPO）
- 13F（机构持仓）

✅ **无缝对接现有系统**
- 统一事件输入格式
- 复用规则过滤
- 复用AI抽取
- 复用评分系统

---

## 快速开始

### 1. 配置邮箱（必须）

编辑 `src/fund_quant/data_sources/sec_edgar/sec_config.py` 第17行：

```python
SEC_USER_AGENT = "fund_quant_system/0.1 (contact: your_email@example.com)"
```

**把邮箱改成你的真实邮箱，否则SEC会拒绝请求！**

### 2. 安装依赖

```bash
uv pip install beautifulsoup4 lxml
```

### 3. 运行测试

```bash
# 单元测试
uv run pytest tests/test_sec_edgar_collector.py -v

# 采集NVDA最近7天的8-K
python scripts/collect_sec_filings.py --tickers NVDA --forms 8-K --days 7

# 采集多个ticker
python scripts/collect_sec_filings.py --tickers NVDA TSLA AAPL --forms 8-K --days 30

# 使用默认股票池
python scripts/collect_sec_filings.py --use-default-tickers --forms 8-K --days 7 --save-json
```

---

## 命令行参数

```bash
python scripts/collect_sec_filings.py [OPTIONS]

选项:
  --tickers NVDA TSLA      # 股票代码列表
  --use-default-tickers    # 使用默认股票池（NVDA/TSLA/AAPL等17只）
  --forms 8-K 10-Q         # 表单类型（默认: 8-K 8-K/A）
  --days 7                 # 最近N天（默认7）
  --since-date 2024-01-01  # 起始日期（与--days二选一）
  --max-per-ticker 100     # 每个ticker最大filings数
  --download               # 下载filing正文（默认开启）
  --save-json              # 保存JSON结果
  --output-dir PATH        # 输出目录
```

---

## 工作流程

```
1. Ticker → CIK映射
   ↓
2. 获取submissions JSON
   ↓
3. 筛选表单类型（8-K）
   ↓
4. 过滤日期（since_date）
   ↓
5. 下载filing正文
   ↓
6. HTML转纯文本
   ↓
7. 截断到30000字符
   ↓
8. 标准化为统一格式
   ↓
9. 写入raw_news或raw_filings
   ↓
10. 进入规则过滤
   ↓
11. AI事件抽取
   ↓
12. 题材标准化
   ↓
13. 评分
```

---

## 数据格式

### Filing元数据

```python
{
    "filing_id": "sec_NVDA_0001045810-24-000123",
    "ticker": "NVDA",
    "cik": "0001045810",
    "company_name": "NVIDIA CORP",
    "form_type": "8-K",
    "accession_number": "0001045810-24-000123",
    "filing_date": "2024-12-31",
    "report_date": "2024-12-31",
    "filing_url": "https://www.sec.gov/Archives/edgar/data/...",
    "content": "清洗后的纯文本..."
}
```

### 统一事件输入格式

```python
{
    "source": "sec_edgar",
    "news_id": "sec_NVDA_0001045810-24-000123",
    "title": "NVDA 8-K 2024-12-31 - NVIDIA CORP",
    "content": "清洗后的纯文本...",
    "publish_time": datetime(...),
    "url": "https://www.sec.gov/Archives/...",
    "ticker": "NVDA",
    "form_type": "8-K"
}
```

---

## 规则过滤建议

对SEC 8-K的规则：

```python
# 8-K默认高优先级
if form_type == "8-K":
    action = "analyze"
    need_ai = True

# 高价值关键词加分
if any(kw in content for kw in HIGH_VALUE_KEYWORDS):
    priority += 10
```

HIGH_VALUE_KEYWORDS包括：
- earnings, guidance, merger, acquisition
- CEO, CFO, resignation
- bankruptcy, restructuring
- share repurchase, dividend
- FDA, partnership, contract

---

## 注意事项

⚠️ **必须遵守SEC Fair Access**
- 请求频率不超过10 req/s
- 默认2 req/s（安全范围1-3 req/s）
- 必须设置User-Agent含邮箱

⚠️ **内容截断**
- 最小长度：100字符（低于此视为无效）
- 最大长度：30000字符（超过截断）
- 用于后续AI抽取

⚠️ **表单优先级**
- 8-K：最高（重大事件）
- 10-Q/10-K：中等（定期报告）
- Form 4：中等（内部交易）
- 13F：低（机构持仓）

---

## 目录结构

```
src/fund_quant/data_sources/sec_edgar/
├── __init__.py
├── sec_config.py              # 配置和规则
├── ticker_mapper.py           # Ticker→CIK映射
├── sec_client.py              # SEC客户端（含限流）
├── filing_collector.py        # 采集filings元数据
├── filing_downloader.py       # 下载和清洗HTML
├── filing_normalizer.py       # 转统一格式
└── README.md

scripts/
└── collect_sec_filings.py     # 命令行入口

tests/
└── test_sec_edgar_collector.py
```

---

## 常见问题

**Q: 为什么请求被拒绝？**
A: 检查User-Agent是否包含邮箱，格式必须是：
```
fund_quant_system/0.1 (contact: your_email@example.com)
```

**Q: CIK如何补齐10位？**
A: 使用 `TickerMapper.pad_cik("1045810")` → `"0001045810"`

**Q: Accession URL如何拼接？**
A:
```python
# 1. 移除CIK前导零: 0001045810 → 1045810
# 2. 移除accession横线: 0001045810-24-000123 → 000104581024000123
# 3. 拼接: https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}
```

**Q: 如何对接现有AI抽取？**
A: FilingNormalizer已转为统一格式，直接传入AIEventExtractor即可。

---

## 后续扩展

- [ ] 接入ClickHouse raw_filings表
- [ ] 8-K专用AI提示词
- [ ] Form 4内部交易分析
- [ ] 13F机构持仓追踪
- [ ] 10-Q/10-K财报关键指标提取
- [ ] S-1 IPO事件监控

---

## 法律说明

- 使用SEC官方免费数据源
- 遵守SEC Fair Access规则
- 不绕过任何限制
- 仅用于个人研究和技术学习
