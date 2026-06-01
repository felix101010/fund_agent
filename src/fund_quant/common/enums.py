"""枚举类型定义"""
from enum import Enum


class DataSource(str, Enum):
    """数据源"""
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    CAILIAN = "cailian"
    JUCHAO = "juchao"
    REUTERS = "reuters"
    REDDIT = "reddit"
    TWITTER = "twitter"


class AssetType(str, Enum):
    """资产类型"""
    STOCK = "stock"
    ETF = "etf"
    INDEX = "index"
    FUND = "fund"


class EventType(str, Enum):
    """事件类型"""
    PRODUCT_RELEASE = "product_release"
    EARNINGS = "earnings"
    REGULATION = "regulation"
    MERGER = "merger"
    INVESTMENT = "investment"
    MACRO = "macro"
    GEOPOLITICS = "geopolitics"


class Sentiment(str, Enum):
    """情绪"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SignalType(str, Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
