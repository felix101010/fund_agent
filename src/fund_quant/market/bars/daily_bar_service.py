"""
日线行情业务服务
负责业务编排：读取配置、调用采集器、写入数据库
"""
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import yaml
import pandas as pd

from fund_quant.market.bars.daily_bar_collector import DailyBarCollector
from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.common.logger import logger


class DailyBarService:
    """日线行情业务服务"""

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        collector: Optional[DailyBarCollector] = None,
        db_client: Optional[ClickHouseClient] = None
    ):
        """
        初始化服务

        Args:
            config_dir: 配置文件目录（默认为项目根目录/configs）
            collector: 数据采集器实例
            db_client: 数据库客户端实例
        """
        # 默认配置目录
        if config_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            config_dir = project_root / 'configs'

        self.config_dir = config_dir

        # 初始化采集器和数据库客户端
        self.collector = collector or DailyBarCollector()
        self.db_client = db_client or ClickHouseClient()

    def collect_theme_indices(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        incremental: bool = False
    ) -> int:
        """
        采集主题指数日线数据

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            incremental: 是否增量更新

        Returns:
            成功采集的记录数
        """
        logger.info("=" * 60)
        logger.info("采集主题指数日线数据")
        logger.info("=" * 60)

        # 读取配置
        config_file = self.config_dir / 'themes' / 'theme_index_mapping.yaml'
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        symbols = []
        for mapping in config['mappings']:
            index_code = mapping['primary_index']['code']
            index_name = mapping['primary_index']['name']
            theme_name = mapping['theme_name']
            symbols.append({
                'symbol': index_code,
                'name': index_name,
                'theme': theme_name
            })

        logger.info(f"加载了 {len(symbols)} 个主题指数")

        # 采集数据
        total_inserted = 0
        for i, item in enumerate(symbols, 1):
            symbol = item['symbol']
            name = item['name']
            theme = item['theme']

            logger.info(f"\n[{i}/{len(symbols)}] {theme} - {name} ({symbol})")

            # 增量模式：查询最后日期
            actual_start_date = start_date
            if incremental:
                last_date = self._get_last_trade_date(symbol, 'INDEX')
                if last_date:
                    actual_start_date = last_date.replace('-', '')
                    logger.info(f"  增量更新，从 {last_date} 开始")

            # 检查是否已有数据（非增量模式）
            if not incremental:
                existing_count = self._count_existing_data(symbol, 'INDEX')
                if existing_count > 0:
                    logger.info(f"  已存在 {existing_count} 条数据，跳过")
                    continue

            # 采集数据
            df = self.collector.collect_index_daily(symbol, actual_start_date, end_date)

            if df is None or len(df) == 0:
                logger.warning(f"  ✗ 无数据")
                continue

            # 写入数据库
            inserted = self._save_to_db(df, symbol, 'INDEX')
            total_inserted += inserted

        logger.info(f"\n总计插入: {total_inserted} 条记录")
        return total_inserted

    def collect_market_indices(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        incremental: bool = False
    ) -> int:
        """
        采集宽基指数日线数据

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            incremental: 是否增量更新

        Returns:
            成功采集的记录数
        """
        logger.info("=" * 60)
        logger.info("采集宽基指数日线数据")
        logger.info("=" * 60)

        # 读取配置
        config_file = self.config_dir / 'market' / 'market_indices.yaml'
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        symbols = []

        # 宽基指数
        for idx in config['market_indices']['broad_market']:
            symbols.append({
                'symbol': idx['symbol'],
                'name': idx['name'],
                'role': idx['role']
            })

        # 风格指数
        for idx in config['market_indices']['style_indices']:
            symbols.append({
                'symbol': idx['symbol'],
                'name': idx['name'],
                'role': idx['role']
            })

        logger.info(f"加载了 {len(symbols)} 个宽基指数")

        # 采集数据
        total_inserted = 0
        for i, item in enumerate(symbols, 1):
            symbol = item['symbol']
            name = item['name']
            role = item['role']

            logger.info(f"\n[{i}/{len(symbols)}] {name} ({symbol}) - {role}")

            # 增量模式
            actual_start_date = start_date
            if incremental:
                last_date = self._get_last_trade_date(symbol, 'INDEX')
                if last_date:
                    actual_start_date = last_date.replace('-', '')
                    logger.info(f"  增量更新，从 {last_date} 开始")

            # 检查已有数据
            if not incremental:
                existing_count = self._count_existing_data(symbol, 'INDEX')
                if existing_count > 0:
                    logger.info(f"  已存在 {existing_count} 条数据，跳过")
                    continue

            # 采集数据
            df = self.collector.collect_index_daily(symbol, actual_start_date, end_date)

            if df is None or len(df) == 0:
                logger.warning(f"  ✗ 无数据")
                continue

            # 写入数据库
            inserted = self._save_to_db(df, symbol, 'INDEX')
            total_inserted += inserted

        logger.info(f"\n总计插入: {total_inserted} 条记录")
        return total_inserted

    def collect_theme_etfs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        incremental: bool = False
    ) -> int:
        """
        采集主题ETF日线数据

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            incremental: 是否增量更新

        Returns:
            成功采集的记录数
        """
        logger.info("=" * 60)
        logger.info("采集主题ETF日线数据")
        logger.info("=" * 60)

        # 读取配置
        config_file = self.config_dir / 'themes' / 'theme_etf_mapping.yaml'
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        symbols = []
        for mapping in config['mappings']:
            etf_code = mapping['etf']['code']
            etf_name = mapping['etf']['name']
            theme_name = mapping['theme_name']
            symbols.append({
                'symbol': etf_code,
                'name': etf_name,
                'theme': theme_name
            })

        logger.info(f"加载了 {len(symbols)} 个主题ETF")

        # 采集数据
        total_inserted = 0
        for i, item in enumerate(symbols, 1):
            symbol = item['symbol']
            name = item['name']
            theme = item['theme']

            logger.info(f"\n[{i}/{len(symbols)}] {theme} - {name} ({symbol})")

            # 增量模式
            actual_start_date = start_date
            if incremental:
                last_date = self._get_last_trade_date(symbol, 'ETF')
                if last_date:
                    actual_start_date = last_date.replace('-', '')
                    logger.info(f"  增量更新，从 {last_date} 开始")

            # 检查已有数据
            if not incremental:
                existing_count = self._count_existing_data(symbol, 'ETF')
                if existing_count > 0:
                    logger.info(f"  已存在 {existing_count} 条数据，跳过")
                    continue

            # 采集数据
            df = self.collector.collect_etf_daily(symbol, actual_start_date, end_date)

            if df is None or len(df) == 0:
                logger.warning(f"  ✗ 无数据")
                continue

            # 写入数据库
            inserted = self._save_to_db(df, symbol, 'ETF')
            total_inserted += inserted

        logger.info(f"\n总计插入: {total_inserted} 条记录")
        return total_inserted

    def collect_all(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        incremental: bool = False
    ) -> Dict[str, int]:
        """
        采集所有类型的日线数据

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            incremental: 是否增量更新

        Returns:
            各类型采集统计
        """
        logger.info("=" * 60)
        logger.info("采集所有日线数据")
        logger.info(f"时间范围: {start_date or '默认'} ~ {end_date or '今天'}")
        logger.info(f"模式: {'增量' if incremental else '全量'}")
        logger.info("=" * 60)

        stats = {}

        # 1. 主题指数
        stats['theme_indices'] = self.collect_theme_indices(start_date, end_date, incremental)

        # 2. 宽基指数
        stats['market_indices'] = self.collect_market_indices(start_date, end_date, incremental)

        # 3. 主题ETF
        stats['theme_etfs'] = self.collect_theme_etfs(start_date, end_date, incremental)

        # 汇总
        logger.info("\n" + "=" * 60)
        logger.info("采集完成汇总")
        logger.info("=" * 60)
        logger.info(f"主题指数: {stats['theme_indices']} 条")
        logger.info(f"宽基指数: {stats['market_indices']} 条")
        logger.info(f"主题ETF: {stats['theme_etfs']} 条")
        logger.info(f"总计: {sum(stats.values())} 条")
        logger.info("=" * 60)

        return stats

    def _get_last_trade_date(self, symbol: str, asset_type: str) -> Optional[str]:
        """
        获取指定证券的最后交易日期

        Args:
            symbol: 证券代码
            asset_type: 资产类型

        Returns:
            最后交易日期 YYYY-MM-DD，无数据返回None
        """
        sql = f"""
        SELECT MAX(trade_date) as last_date
        FROM daily_bars
        WHERE symbol = '{symbol}' AND asset_type = '{asset_type}'
        """
        df = self.db_client.query_df(sql)

        if df is None or len(df) == 0 or df['last_date'].iloc[0] is None:
            return None

        last_date = df['last_date'].iloc[0]

        # 转换为字符串
        if isinstance(last_date, str):
            return last_date
        else:
            return last_date.strftime('%Y-%m-%d')

    def _count_existing_data(self, symbol: str, asset_type: str) -> int:
        """
        统计已有数据条数

        Args:
            symbol: 证券代码
            asset_type: 资产类型

        Returns:
            数据条数
        """
        sql = f"""
        SELECT COUNT(*) as cnt
        FROM daily_bars
        WHERE symbol = '{symbol}' AND asset_type = '{asset_type}'
        """
        df = self.db_client.query_df(sql)

        if df is None or len(df) == 0:
            return 0

        return int(df['cnt'].iloc[0])

    def _save_to_db(self, df: pd.DataFrame, symbol: str, asset_type: str) -> int:
        """
        保存数据到数据库，自动去重

        Args:
            df: 数据DataFrame
            symbol: 证券代码
            asset_type: 资产类型

        Returns:
            插入的记录数
        """
        if df is None or len(df) == 0:
            return 0

        try:
            # 获取日期范围
            min_date = df['trade_date'].min()
            max_date = df['trade_date'].max()

            # 删除该日期范围内的旧数据（避免重复）
            delete_sql = f"""
            DELETE FROM daily_bars
            WHERE symbol = '{symbol}'
              AND asset_type = '{asset_type}'
              AND trade_date >= '{min_date}'
              AND trade_date <= '{max_date}'
            """
            self.db_client.execute(delete_sql)

            # 转换为字典列表
            records = df.to_dict('records')

            # 批量插入
            inserted = self.db_client.insert_many('daily_bars', records)

            logger.info(f"  ✓ 成功插入: {inserted} 条数据")

            return inserted

        except Exception as e:
            logger.error(f"  ✗ 写入数据库失败: {e}")
            return 0
