"""
SEC EDGAR 配置模块
包含User-Agent、限流、表单类型等配置

遵守SEC Fair Access规则：
- 请求频率不超过10 req/s
- 默认控制在1-3 req/s
- 必须设置明确的User-Agent
"""
from typing import List

# SEC Fair Access配置
SEC_REQUEST_RATE = 2  # 每秒请求数（默认2，安全范围1-3）
SEC_MAX_RATE = 10  # SEC规定的最大请求数（绝不能超过）
SEC_TIMEOUT = 30  # 请求超时时间（秒）

# User-Agent（必须设置，否则SEC会拒绝请求）
SEC_USER_AGENT = "fund_quant_system/0.1 (contact: your_email@example.com)"

# SEC数据源URL
SEC_BASE_URL = "https://www.sec.gov"
SEC_DATA_URL = "https://data.sec.gov"
SEC_ARCHIVES_URL = f"{SEC_BASE_URL}/Archives/edgar/data"

# Ticker映射数据源
SEC_TICKER_TXT_URL = f"{SEC_BASE_URL}/include/ticker.txt"
SEC_TICKER_JSON_URL = f"{SEC_BASE_URL}/files/company_tickers.json"

# 支持的表单类型
FORM_TYPES = {
    "8-K": {
        "description": "Current Report (Material Events)",
        "priority": "high",
        "default_action": "analyze"
    },
    "8-K/A": {
        "description": "Current Report Amendment",
        "priority": "high",
        "default_action": "analyze"
    },
    "10-Q": {
        "description": "Quarterly Report",
        "priority": "medium",
        "default_action": "candidate"
    },
    "10-K": {
        "description": "Annual Report",
        "priority": "medium",
        "default_action": "candidate"
    },
    "10-Q/A": {
        "description": "Quarterly Report Amendment",
        "priority": "low",
        "default_action": "watch"
    },
    "10-K/A": {
        "description": "Annual Report Amendment",
        "priority": "low",
        "default_action": "watch"
    },
    "4": {
        "description": "Insider Trading",
        "priority": "medium",
        "default_action": "candidate"
    },
    "S-1": {
        "description": "IPO Registration",
        "priority": "high",
        "default_action": "analyze"
    },
    "13F-HR": {
        "description": "Institutional Holdings",
        "priority": "low",
        "default_action": "watch"
    }
}

# 8-K高价值关键词
HIGH_VALUE_KEYWORDS = [
    "earnings", "results of operations", "financial statements",
    "guidance", "outlook", "merger", "acquisition", "definitive agreement",
    "material agreement", "CEO", "CFO", "resignation", "appointment",
    "bankruptcy", "restructuring", "share repurchase", "stock split",
    "dividend", "offering", "convertible notes", "private placement",
    "litigation", "investigation", "FDA", "contract", "partnership"
]

# 重点股票池（美股）
DEFAULT_TICKERS = [
    "NVDA", "TSLA", "AAPL", "MSFT", "AMD", "AVGO",
    "META", "GOOGL", "AMZN", "PLTR", "COIN", "MSTR",
    "NFLX", "INTC", "QCOM", "TSM", "ASML"
]

# 正文截断长度（字符数）
CONTENT_MIN_LENGTH = 100  # 最小长度，低于此长度视为无效
CONTENT_MAX_LENGTH = 30000  # 最大长度，超过此长度截断


__all__ = [
    'SEC_REQUEST_RATE',
    'SEC_MAX_RATE',
    'SEC_TIMEOUT',
    'SEC_USER_AGENT',
    'SEC_BASE_URL',
    'SEC_DATA_URL',
    'SEC_ARCHIVES_URL',
    'SEC_TICKER_TXT_URL',
    'SEC_TICKER_JSON_URL',
    'FORM_TYPES',
    'HIGH_VALUE_KEYWORDS',
    'DEFAULT_TICKERS',
    'CONTENT_MIN_LENGTH',
    'CONTENT_MAX_LENGTH'
]
