"""
因子计算通用函数
封装常用的因子计算逻辑，包括收益率、移动均线、Alpha等
"""
from typing import List
import pandas as pd
import numpy as np


def calculate_returns(df: pd.DataFrame, periods: List[int] = [1, 3, 5, 20, 60]) -> pd.DataFrame:
    """
    计算多周期收益率

    Args:
        df: DataFrame，必须包含 'close' 列，且已按 trade_date 升序排序
        periods: 周期列表，单位为交易日

    Returns:
        在原 DataFrame 基础上增加 ret_1d, ret_3d, ret_5d, ret_20d, ret_60d 列

    Notes:
        - 使用 shift 计算收益率: (close / close.shift(period) - 1) * 100
        - 前 N 个交易日的收益率为 NaN
        - 收益率单位为百分比(%)
    """
    result = df.copy()

    for period in periods:
        result[f'ret_{period}d'] = (result['close'] / result['close'].shift(period) - 1) * 100

    return result


def calculate_moving_averages(
    df: pd.DataFrame,
    windows: List[int] = [5, 10, 20, 30, 60, 250]
) -> pd.DataFrame:
    """
    计算移动均线

    Args:
        df: DataFrame，必须包含 'close' 列，且已按 trade_date 升序排序
        windows: 窗口期列表，单位为交易日

    Returns:
        在原 DataFrame 基础上增加 ma5, ma10, ma20, ma30, ma60, ma250 列

    Notes:
        - 使用 rolling().mean() 计算简单移动平均
        - 前 N 个交易日的均线为 NaN
    """
    result = df.copy()

    for window in windows:
        result[f'ma{window}'] = result['close'].rolling(window).mean()

    return result


def calculate_alpha(
    theme_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    periods: List[int] = [5, 20, 60]
) -> pd.DataFrame:
    """
    计算 Alpha（超额收益）

    Args:
        theme_df: 主题收益率 DataFrame，必须包含 ret_5d, ret_20d, ret_60d 列
        benchmark_df: 基准收益率 DataFrame，必须包含 ret_5d, ret_20d, ret_60d 列
                      列名会被重命名为 hs300_ret_5d, hs300_ret_20d, hs300_ret_60d
        periods: 周期列表

    Returns:
        在 theme_df 基础上增加 alpha_5d, alpha_20d, alpha_60d 列

    Notes:
        - Alpha = 主题收益率 - 基准收益率
        - 按 trade_date 进行左连接对齐
        - 如果基准数据缺失，Alpha 为 NaN
    """
    result = theme_df.copy()

    # 准备基准数据
    benchmark_cols = ['trade_date'] + [f'ret_{p}d' for p in periods]
    benchmark_renamed = benchmark_df[benchmark_cols].copy()

    # 重命名基准列
    rename_map = {f'ret_{p}d': f'hs300_ret_{p}d' for p in periods}
    benchmark_renamed = benchmark_renamed.rename(columns=rename_map)

    # 合并基准数据
    result = result.merge(benchmark_renamed, on='trade_date', how='left')

    # 计算 Alpha
    for period in periods:
        ret_col = f'ret_{period}d'
        benchmark_col = f'hs300_ret_{period}d'
        alpha_col = f'alpha_{period}d'

        if ret_col in result.columns and benchmark_col in result.columns:
            result[alpha_col] = result[ret_col] - result[benchmark_col]

    return result


def calculate_amount_ratio(
    df: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20
) -> pd.DataFrame:
    """
    计算成交额倍数

    Args:
        df: DataFrame，必须包含 'amount' 列，且已按 trade_date 升序排序
        short_window: 短期窗口（默认5日）
        long_window: 长期窗口（默认20日）

    Returns:
        在原 DataFrame 基础上增加以下列:
        - amount_ma5: 5日平均成交额
        - amount_ma20: 20日平均成交额
        - amount_ratio_1d: 当日成交额 / 20日平均成交额
        - amount_ratio_5d: 5日平均成交额 / 20日平均成交额

    Notes:
        - 避免除以0，当分母为0时结果为0
        - 前 N 个交易日的均线和倍数为 NaN 或 0
    """
    result = df.copy()

    # 计算成交额均线
    result[f'amount_ma{short_window}'] = result['amount'].rolling(short_window).mean()
    result[f'amount_ma{long_window}'] = result['amount'].rolling(long_window).mean()

    # 计算倍数（避免除以0）
    result['amount_ratio_1d'] = np.where(
        result[f'amount_ma{long_window}'] > 0,
        result['amount'] / result[f'amount_ma{long_window}'],
        0
    )

    result['amount_ratio_5d'] = np.where(
        result[f'amount_ma{long_window}'] > 0,
        result[f'amount_ma{short_window}'] / result[f'amount_ma{long_window}'],
        0
    )

    return result


def calculate_trend_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算趋势得分

    Args:
        df: DataFrame，必须包含 'close', 'ma5', 'ma20', 'ma60' 列

    Returns:
        在原 DataFrame 基础上增加以下列:
        - above_ma20: 价格是否在MA20上方 (0/1)
        - above_ma60: 价格是否在MA60上方 (0/1)
        - ma20_gt_ma60: MA20是否在MA60上方 (0/1)
        - ma5_gt_ma20: MA5是否在MA20上方 (0/1)
        - trend_score: 趋势得分 (0-4)

    Notes:
        - trend_score = above_ma20 + above_ma60 + ma20_gt_ma60 + ma5_gt_ma20
        - 得分越高，多头趋势越强
        - 如果均线为 NaN，对应信号为 0
    """
    result = df.copy()

    # 价格相对均线位置
    result['above_ma20'] = (result['close'] > result['ma20']).astype(int)
    result['above_ma60'] = (result['close'] > result['ma60']).astype(int)

    # 均线多头排列
    result['ma20_gt_ma60'] = (result['ma20'] > result['ma60']).astype(int)
    result['ma5_gt_ma20'] = (result['ma5'] > result['ma20']).astype(int)

    # 趋势得分（0-4分）
    result['trend_score'] = (
        result['above_ma20'] +
        result['above_ma60'] +
        result['ma20_gt_ma60'] +
        result['ma5_gt_ma20']
    )

    return result
