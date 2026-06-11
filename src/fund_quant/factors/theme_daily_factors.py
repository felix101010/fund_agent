"""
主题日度因子计算器
负责从数据库读取数据，计算主题强度因子，并返回结果DataFrame
"""
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import yaml

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.common.logger import logger
from fund_quant.factors.factor_utils import (
    calculate_returns,
    calculate_moving_averages,
    calculate_alpha,
    calculate_amount_ratio,
    calculate_trend_score
)
from fund_quant.factors.models import FACTOR_COLUMNS


class ThemeDailyFactorCalculator:
    """主题日度因子计算器"""

    def __init__(
        self,
        clickhouse_client: ClickHouseClient,
        theme_config: pd.DataFrame,
        benchmark_symbol: str = "000300.SH"
    ):
        """
        初始化因子计算器

        Args:
            clickhouse_client: ClickHouse客户端
            theme_config: 主题配置DataFrame，包含 theme_id, theme_name, index_symbol, etf_symbol
            benchmark_symbol: 基准指数代码（默认沪深300）
        """
        self.client = clickhouse_client
        self.theme_config = theme_config
        self.benchmark_symbol = benchmark_symbol

    def calculate(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        theme_ids: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        计算主题因子

        Args:
            start_date: 开始日期（YYYY-MM-DD），None表示全部
            end_date: 结束日期（YYYY-MM-DD），None表示今天
            theme_ids: 指定主题ID列表，None表示全部主题

        Returns:
            主题因子DataFrame，包含 FACTOR_COLUMNS 定义的所有列
        """
        logger.info("=" * 60)
        logger.info("主题日度因子计算")
        logger.info("=" * 60)

        # 1. 筛选要计算的主题
        if theme_ids:
            themes_df = self.theme_config[self.theme_config['theme_id'].isin(theme_ids)].copy()
            logger.info(f"\n步骤1: 计算指定主题: {theme_ids}")
        else:
            themes_df = self.theme_config.copy()
            logger.info(f"\n步骤1: 计算所有主题")

        logger.info(f"✓ 加载了 {len(themes_df)} 个主题")

        # 2. 获取基准数据（沪深300）
        logger.info(f"\n步骤2: 获取基准数据 ({self.benchmark_symbol})")
        benchmark_df = self._fetch_daily_bars(
            self.benchmark_symbol,
            'INDEX',
            start_date,
            end_date
        )

        if benchmark_df is None or len(benchmark_df) == 0:
            logger.error(f"✗ 基准数据为空，请先采集 {self.benchmark_symbol} 数据")
            return pd.DataFrame(columns=FACTOR_COLUMNS)

        logger.info(f"✓ 基准数据: {len(benchmark_df)} 行")

        # 计算基准收益率
        benchmark_df = calculate_returns(benchmark_df, [5, 20, 60])

        # 3. 逐个主题计算因子
        logger.info("\n步骤3: 计算各主题因子")
        all_factors = []

        for idx, theme in themes_df.iterrows():
            theme_id = theme['theme_id']
            theme_name = theme['theme_name']
            index_symbol = theme['index_symbol']
            etf_symbol = theme['etf_symbol']

            logger.info(f"\n  [{idx+1}/{len(themes_df)}] {theme_name} ({theme_id})")
            logger.info(f"    指数: {index_symbol}, ETF: {etf_symbol}")

            # 计算单个主题的因子
            theme_factor = self._calculate_one_theme(
                theme_id, theme_name, index_symbol, etf_symbol,
                benchmark_df, start_date, end_date
            )

            if theme_factor is not None and len(theme_factor) > 0:
                all_factors.append(theme_factor)
                logger.info(f"    ✓ 计算完成: {len(theme_factor)} 行有效数据")
            else:
                logger.warning(f"    ⚠ 无有效数据")

        # 4. 合并所有主题数据
        if len(all_factors) == 0:
            logger.warning("✗ 没有计算出任何因子数据")
            return pd.DataFrame(columns=FACTOR_COLUMNS)

        logger.info(f"\n步骤4: 合并数据")
        final_df = pd.concat(all_factors, ignore_index=True)
        logger.info(f"✓ 总计 {len(final_df)} 行因子数据")

        # 5. 统计信息
        logger.info("\n" + "=" * 60)
        logger.info("计算完成统计")
        logger.info("=" * 60)
        logger.info(f"主题数量: {len(themes_df)}")
        logger.info(f"成功计算: {len(all_factors)}")
        logger.info(f"总记录数: {len(final_df)}")

        if len(final_df) > 0:
            min_date = final_df['trade_date'].min()
            max_date = final_df['trade_date'].max()
            logger.info(f"日期范围: {min_date} ~ {max_date}")

        logger.info("=" * 60)

        return final_df

    def _calculate_one_theme(
        self,
        theme_id: str,
        theme_name: str,
        index_symbol: str,
        etf_symbol: str,
        benchmark_df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        计算单个主题的因子

        Args:
            theme_id: 主题ID
            theme_name: 主题名称
            index_symbol: 指数代码
            etf_symbol: ETF代码
            benchmark_df: 基准数据（已计算收益率）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            主题因子DataFrame，如果失败返回None
        """
        # 1. 获取指数数据
        index_df = self._fetch_daily_bars(index_symbol, 'INDEX', start_date, end_date)
        if index_df is None or len(index_df) == 0:
            logger.warning(f"    ⚠ 指数数据为空")
            return None

        # 2. 获取ETF数据
        etf_df = self._fetch_daily_bars(etf_symbol, 'ETF', start_date, end_date)
        if etf_df is None or len(etf_df) == 0:
            logger.warning(f"    ⚠ ETF数据为空")
            return None

        # 3. 计算指数指标
        index_df = calculate_returns(index_df, [1, 3, 5, 20, 60])
        index_df = calculate_moving_averages(index_df, [5, 10, 20, 30, 60, 250])
        index_df = calculate_trend_score(index_df)

        # 重命名列
        index_df = index_df.rename(columns={
            'ma5': 'index_ma5',
            'ma10': 'index_ma10',
            'ma20': 'index_ma20',
            'ma30': 'index_ma30',
            'ma60': 'index_ma60',
            'ma250': 'index_ma250',
            'close': 'index_close'
        })

        # 4. 计算ETF成交额指标
        etf_df = calculate_amount_ratio(etf_df, short_window=5, long_window=20)
        etf_df = etf_df.rename(columns={
            'close': 'etf_close',
            'amount': 'etf_amount'
        })

        # 5. 合并指数和ETF数据（按日期对齐）
        merged_df = index_df.merge(
            etf_df[['trade_date', 'etf_close', 'etf_amount', 'amount_ma5', 'amount_ma20', 'amount_ratio_1d', 'amount_ratio_5d']],
            on='trade_date',
            how='inner'
        )

        # 6. 计算Alpha（合并基准数据）
        merged_df = calculate_alpha(merged_df, benchmark_df, [5, 20, 60])

        # 7. 添加主题信息
        merged_df['theme_id'] = theme_id
        merged_df['theme_name'] = theme_name
        merged_df['index_symbol'] = index_symbol
        merged_df['etf_symbol'] = etf_symbol

        # 8. 选择需要的列
        merged_df = merged_df[FACTOR_COLUMNS]

        # 9. 删除数据不足的行（前期数据不足以计算60日收益率和60日均线）
        merged_df = merged_df.dropna(subset=['ret_60d', 'index_ma60'])

        return merged_df

    def _fetch_daily_bars(
        self,
        symbol: str,
        asset_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        从数据库获取日线数据

        Args:
            symbol: 证券代码
            asset_type: 资产类型 ('INDEX' 或 'ETF')
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）

        Returns:
            日线数据DataFrame，包含 trade_date, open, high, low, close, volume, amount
        """
        where_clause = f"symbol = '{symbol}' AND asset_type = '{asset_type}'"

        # 如果指定了日期范围，需要额外取更多数据以计算MA250
        if start_date:
            # 往前推300天以确保有足够数据计算MA250
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            extended_start = (start_dt - timedelta(days=400)).strftime('%Y-%m-%d')
            where_clause += f" AND trade_date >= '{extended_start}'"

        if end_date:
            where_clause += f" AND trade_date <= '{end_date}'"

        sql = f"""
        SELECT
            trade_date,
            open,
            high,
            low,
            close,
            volume,
            amount
        FROM daily_bars
        WHERE {where_clause}
        ORDER BY trade_date
        """

        df = self.client.query_df(sql)

        if df is None or len(df) == 0:
            return None

        # 转换日期和数值类型
        df['trade_date'] = pd.to_datetime(df['trade_date'])

        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # 如果指定了start_date，过滤只保留所需范围（但保留了用于计算的历史数据）
        # 这个过滤会在最后计算完成后由调用方处理

        return df


def load_theme_config(config_path: Path) -> pd.DataFrame:
    """
    加载主题配置文件

    Args:
        config_path: 配置文件路径（theme_etf_mapping.yaml）

    Returns:
        主题配置DataFrame，包含 theme_id, theme_name, index_symbol, etf_symbol
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    themes = []
    for mapping in config['mappings']:
        themes.append({
            'theme_id': mapping['theme_id'],
            'theme_name': mapping['theme_name'],
            'index_symbol': mapping['primary_index']['code'],
            'etf_symbol': mapping['etf']['code']
        })

    return pd.DataFrame(themes)
