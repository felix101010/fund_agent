"""
股票代码合法性验证器
用于清洗 AI 输出中的 related_stocks，过滤掉非股票代码
"""
import re
from typing import List, Dict, Any, Union


# 明确禁止的伪股票代码
BLOCKED_CODES = {
    # 常见英文缩写
    "AI", "CEO", "CFO", "CTO", "CIO", "COO",
    "ETF", "IPO", "PE", "VC", "LP", "GP",

    # 宏观经济指标
    "GDP", "CPI", "PPI", "PMI", "PCE", "FOMC",

    # 技术/产品缩写
    "HBM", "MLCC", "CPO", "PCB", "GPU", "CPU", "NPU", "TPU",
    "ASIC", "FPGA", "LLM", "API", "SDK", "IDE",

    # 能源/商品
    "WTI", "EIA", "OPEC", "LNG", "LPG",

    # 国际组织
    "G7", "G20", "WTO", "IMF", "WHO",

    # 其他
    "AIPPI", "UNESCO", "NATO", "ASEAN",
}

# 美股白名单（只允许这些 ticker）
US_TICKER_WHITELIST = {
    # 科技巨头
    "NVDA", "TSLA", "AAPL", "MSFT", "META", "GOOGL", "GOOG", "AMZN",

    # 半导体
    "AMD", "INTC", "AVGO", "MU", "QCOM", "TXN", "AMAT", "LRCX", "KLAC",
    "ASML", "TSM", "ARM", "MRVL", "SNPS", "CDNS",

    # 云计算/软件
    "ORCL", "CRM", "ADBE", "NOW", "SNOW", "DDOG", "MDB",

    # 新能源/电动车
    "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI",

    # 其他重点
    "NFLX", "DIS", "BA", "CAT", "GE", "JPM", "BAC", "V", "MA",
}

# 明显不合理的公司名片段
INVALID_NAME_FRAGMENTS = [
    "用于人工智能",
    "在北京会见",
    "国际保护知识产权协会",
    "出席会议",
    "发表声明",
    "联合国",
    "6月15日",
    "月",
    "年",
    "今日",
    "明日",
    "昨日",
]


def is_valid_stock_code(code: str) -> bool:
    """
    判断是否为合法股票代码

    Args:
        code: 股票代码

    Returns:
        是否合法
    """
    if not code:
        return False

    code = code.strip().upper()

    # 检查黑名单
    if code in BLOCKED_CODES:
        return False

    # A股：6位数字 + .SH/.SZ/.BJ
    if re.match(r'^\d{6}\.(SH|SZ|BJ)$', code):
        return True

    # 港股：5位数字 + .HK
    if re.match(r'^\d{5}\.HK$', code):
        return True

    # 美股：必须在白名单中
    if code in US_TICKER_WHITELIST:
        return True

    # 其他都不认为是合法股票
    return False


def is_reasonable_company_name(name: str) -> bool:
    """
    判断是否为合理的公司名

    Args:
        name: 公司名称

    Returns:
        是否合理
    """
    if not name:
        return True  # 允许空名称

    # 长度检查
    if len(name) > 30:
        return False

    # 检查非法片段
    for fragment in INVALID_NAME_FRAGMENTS:
        if fragment in name:
            return False

    return True


def clean_related_stocks(stocks: Union[List[Dict], List[Any]]) -> List[Dict]:
    """
    清洗 related_stocks，过滤掉非股票代码

    Args:
        stocks: 股票列表，可以是 list[dict] 或 list[object]

    Returns:
        清洗后的股票列表（list[dict]）
    """
    if not stocks:
        return []

    cleaned = []
    seen_codes = set()

    for stock in stocks:
        try:
            # 提取字段（兼容 dict 和 object）
            if isinstance(stock, dict):
                code = stock.get('code', '').strip()
                name = stock.get('name', '').strip()
            else:
                code = getattr(stock, 'code', '').strip()
                name = getattr(stock, 'name', '').strip()

            # 跳过空代码
            if not code:
                continue

            # 代码合法性检查
            if not is_valid_stock_code(code):
                continue

            # 公司名合理性检查
            if not is_reasonable_company_name(name):
                continue

            # 去重（按 code）
            code_upper = code.upper()
            if code_upper in seen_codes:
                continue

            seen_codes.add(code_upper)

            # 保留
            cleaned.append({
                'code': code,
                'name': name,
            })

        except Exception:
            # 单个股票异常不影响其他股票
            continue

    return cleaned


__all__ = [
    'is_valid_stock_code',
    'is_reasonable_company_name',
    'clean_related_stocks',
    'BLOCKED_CODES',
    'US_TICKER_WHITELIST',
]
