"""
日线行情数据采集器
负责从 Tushare 拉取日线数据
"""
import time
from datetime import datetime, date
from typing import Optional, List
import pandas as pd

from fund_quant.market.tushare_provider import get_tushare_pro
from fund_quant.market.bars.models import AssetType
from fund_quant.common.logger import logger


class DailyBarCollector:
    """日线行情采集器"""

    def __init__(self, rate_limit_sleep: float = 0.5):
        """
        初始化采集器

        Args:
            rate_limit_sleep: API请求间隔（秒）
        """
        self.pro = get_tushare_pro()
        self.rate_limit_sleep = rate_limit_sleep

    def collect_index_daily(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        采集指数日线数据

        Args:
            symbol: 指数代码（如 000300.SH）
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            标准化的DataFrame，字段与DailyBar模型对齐
        """
        try:
            df = self.pro.index_daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                return None

            # 标准化字段
            df = self._standardize_dataframe(df, symbol, 'INDEX')

            # 限流
            time.sleep(self.rate_limit_sleep)

            return df

        except Exception as e:
            logger.error(f"采集指数日线失败 {symbol}: {e}")
            return None

    def collect_etf_daily(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        采集ETF日线数据

        Args:
            symbol: ETF代码（如 510300.SH）
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            标准化的DataFrame
        """
        try:
            df = self.pro.fund_daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                return None

            # 标准化字段
            df = self._standardize_dataframe(df, symbol, 'ETF')

            # 限流
            time.sleep(self.rate_limit_sleep)

            return df

        except Exception as e:
            logger.error(f"采集ETF日线失败 {symbol}: {e}")
            return None

    def collect_stock_daily(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        采集股票日线数据

        Args:
            symbol: 股票代码（如 600519.SH）
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            标准化的DataFrame
        """
        try:
            df = self.pro.daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                return None

            # 标准化字段
            df = self._standardize_dataframe(df, symbol, 'STOCK')

            # 限流
            time.sleep(self.rate_limit_sleep)

            return df

        except Exception as e:
            logger.error(f"采集股票日线失败 {symbol}: {e}")
            return None

    def collect_daily(
        self,
        symbol: str,
        asset_type: AssetType,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        根据资产类型自动选择接口采集日线数据

        Args:
            symbol: 证券代码
            asset_type: 资产类型（INDEX/ETF/STOCK）
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            标准化的DataFrame
        """
        if asset_type == 'INDEX':
            return self.collect_index_daily(symbol, start_date, end_date)
        elif asset_type == 'ETF':
            return self.collect_etf_daily(symbol, start_date, end_date)
        elif asset_type == 'STOCK':
            return self.collect_stock_daily(symbol, start_date, end_date)
        else:
            raise ValueError(f"不支持的资产类型: {asset_type}")

    def _standardize_dataframe(
        self,
        df: pd.DataFrame,
        symbol: str,
        asset_type: AssetType
    ) -> pd.DataFrame:
        """
        标准化DataFrame字段

        Args:
            df: Tushare返回的原始DataFrame
            symbol: 证券代码
            asset_type: 资产类型

        Returns:
            标准化后的DataFrame，字段与DailyBar模型对齐
        """
        # 转换日期格式
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d').dt.date

        # 字段映射和重命名
        field_mapping = {
            'ts_code': 'symbol',
            'vol': 'volume',  # 成交量（手）
            'amount': 'amount'  # 成交额（千元，需要转换）
        }

        df = df.rename(columns=field_mapping)

        # 确保symbol字段正确
        df['symbol'] = symbol

        # 添加资产类型
        df['asset_type'] = asset_type

        # 处理NaN值：用close价格填充open/high/low（处理部分指数早期数据缺失）
        if df['open'].isna().any() or df['high'].isna().any() or df['low'].isna().any():
            df['open'] = df['open'].fillna(df['close'])
            df['high'] = df['high'].fillna(df['close'])
            df['low'] = df['low'].fillna(df['close'])

        # 转换成交额单位：千元 -> 元
        if 'amount' in df.columns:
            df['amount'] = df['amount'] * 1000

        # 添加数据源和创建时间
        df['source'] = 'tushare'
        df['created_at'] = datetime.now()

        # 选择需要的字段，保持与DailyBar模型一致
        columns = [
            'symbol', 'asset_type', 'trade_date',
            'open', 'high', 'low', 'close',
            'pre_close', 'pct_chg', 'volume', 'amount',
            'source', 'created_at'
        ]

        # 确保所有字段都存在
        for col in columns:
            if col not in df.columns:
                df[col] = None

        df = df[columns]

        # 按日期升序排序
        df = df.sort_values('trade_date')

        return df

    def collect_batch(
        self,
        symbols: List[str],
        asset_type: AssetType,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        批量采集日线数据

        Args:
            symbols: 证券代码列表
            asset_type: 资产类型
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            合并后的DataFrame
        """
        all_data = []

        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{len(symbols)}] 采集 {asset_type} {symbol}")

            df = self.collect_daily(symbol, asset_type, start_date, end_date)

            if df is not None and len(df) > 0:
                all_data.append(df)
                logger.info(f"  ✓ 成功: {len(df)} 条数据")
            else:
                logger.warning(f"  ✗ 无数据")

        if len(all_data) == 0:
            return pd.DataFrame()

        # 合并所有数据
        result = pd.concat(all_data, ignore_index=True)

        return result
