"""
主题因子数据模型
定义主题日度因子的字段结构
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class ThemeDailyFactor:
    """主题日度因子数据模型"""

    # 基础信息
    trade_date: date
    theme_id: str
    theme_name: str
    index_symbol: str
    etf_symbol: str

    # 价格
    index_close: float
    etf_close: float

    # 收益率（基于指数）
    ret_1d: Optional[float] = None
    ret_3d: Optional[float] = None
    ret_5d: Optional[float] = None
    ret_20d: Optional[float] = None
    ret_60d: Optional[float] = None

    # 基准收益率（沪深300）
    hs300_ret_5d: Optional[float] = None
    hs300_ret_20d: Optional[float] = None
    hs300_ret_60d: Optional[float] = None

    # Alpha（超额收益）
    alpha_5d: Optional[float] = None
    alpha_20d: Optional[float] = None
    alpha_60d: Optional[float] = None

    # 成交额指标（基于ETF）
    etf_amount: Optional[float] = None
    amount_ma5: Optional[float] = None
    amount_ma20: Optional[float] = None
    amount_ratio_1d: Optional[float] = None
    amount_ratio_5d: Optional[float] = None

    # 指数均线
    index_ma5: Optional[float] = None
    index_ma10: Optional[float] = None
    index_ma20: Optional[float] = None
    index_ma30: Optional[float] = None
    index_ma60: Optional[float] = None
    index_ma250: Optional[float] = None

    # 趋势状态
    above_ma20: int = 0
    above_ma60: int = 0
    ma20_gt_ma60: int = 0
    ma5_gt_ma20: int = 0
    trend_score: int = 0


# 因子字段定义（用于数据库和DataFrame列名）
FACTOR_COLUMNS = [
    'trade_date', 'theme_id', 'theme_name', 'index_symbol', 'etf_symbol',
    'index_close', 'etf_close',
    'ret_1d', 'ret_3d', 'ret_5d', 'ret_20d', 'ret_60d',
    'hs300_ret_5d', 'hs300_ret_20d', 'hs300_ret_60d',
    'alpha_5d', 'alpha_20d', 'alpha_60d',
    'etf_amount', 'amount_ma5', 'amount_ma20', 'amount_ratio_1d', 'amount_ratio_5d',
    'index_ma5', 'index_ma10', 'index_ma20', 'index_ma30', 'index_ma60', 'index_ma250',
    'above_ma20', 'above_ma60', 'ma20_gt_ma60', 'ma5_gt_ma20', 'trend_score'
]
