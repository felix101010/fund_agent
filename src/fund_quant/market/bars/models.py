"""
日线行情数据模型
"""
from datetime import date, datetime
from typing import Optional, Literal
from dataclasses import dataclass


AssetType = Literal['INDEX', 'ETF', 'STOCK']


@dataclass
class DailyBar:
    """日线行情数据模型"""

    symbol: str
    asset_type: AssetType
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    pre_close: Optional[float] = None
    pct_chg: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    source: str = 'tushare'
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """数据验证和默认值设置"""
        if self.created_at is None:
            self.created_at = datetime.now()

        # 验证OHLC关系
        if self.high < self.low:
            raise ValueError(f"Invalid OHLC: high({self.high}) < low({self.low})")

        if self.high < self.open or self.high < self.close:
            raise ValueError(f"Invalid OHLC: high not the highest")

        if self.low > self.open or self.low > self.close:
            raise ValueError(f"Invalid OHLC: low not the lowest")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'asset_type': self.asset_type,
            'trade_date': self.trade_date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'pre_close': self.pre_close,
            'pct_chg': self.pct_chg,
            'volume': self.volume,
            'amount': self.amount,
            'source': self.source,
            'created_at': self.created_at
        }
