#!/usr/bin/env python
"""
证券主数据采集脚本
从 Tushare 采集 ETF、指数、股票的基础信息并写入 symbol_master 表
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.market.tushare_provider import (
    get_tushare_pro,
    fetch_etf_basic
)
from fund_quant.data.storage import ClickHouseClient
from fund_quant.common.logger import logger


class SymbolCollector:
    """证券主数据采集器"""

    def __init__(self, source: str = 'tushare'):
        """
        初始化采集器

        Args:
            source: 数据源名称
        """
        self.source = source
        self.client = ClickHouseClient()
        self.job_id = None
        self.start_time = datetime.now()

    def _convert_date(self, date_str: Optional[str]) -> Optional[date]:
        """
        转换日期字符串为 date 对象

        Args:
            date_str: 日期字符串 YYYYMMDD

        Returns:
            date 对象或 None
        """
        if not date_str or pd.isna(date_str) or str(date_str).strip() == '':
            return None

        try:
            date_str = str(date_str).strip()
            return datetime.strptime(date_str, '%Y%m%d').date()
        except Exception as e:
            logger.warning(f"日期转换失败: {date_str}, 错误: {e}")
            return None

    def _normalize_etf_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        标准化 ETF 数据为 symbol_master 格式

        Args:
            df: Tushare 返回的 ETF 数据

        Returns:
            标准化后的数据列表
        """
        rows = []

        for _, row in df.iterrows():
            # 判断状态
            delist_date = self._convert_date(row.get('delist_date'))
            status = 'delisted' if delist_date else 'active'

            # 提取交易所
            ts_code = row['ts_code']
            exchange = ts_code.split('.')[-1] if '.' in ts_code else 'UNKNOWN'

            normalized_row = {
                'symbol': ts_code,
                'name': row['name'],
                'asset_type': 'ETF',
                'exchange': exchange,
                'list_date': self._convert_date(row.get('list_date')),
                'delist_date': delist_date,
                'status': status,
                'fund_type': row.get('fund_type'),
                'source': self.source,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            rows.append(normalized_row)

        return rows

    def _normalize_index_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        标准化指数数据为 symbol_master 格式

        Args:
            df: Tushare 返回的指数数据

        Returns:
            标准化后的数据列表
        """
        rows = []

        for _, row in df.iterrows():
            # 指数一般没有退市日期
            delist_date = None
            status = 'active'

            # 提取交易所
            ts_code = row['ts_code']
            exchange = ts_code.split('.')[-1] if '.' in ts_code else 'UNKNOWN'

            # 转换日期
            list_date = self._convert_date(row.get('base_date'))

            # 跳过没有上市日期的记录
            if list_date is None:
                logger.warning(f"跳过无上市日期的指数: {ts_code} {row['name']}")
                continue

            normalized_row = {
                'symbol': ts_code,
                'name': row['name'],
                'asset_type': 'INDEX',
                'exchange': exchange,
                'list_date': list_date,
                'delist_date': delist_date,
                'status': status,
                'fund_type': None,
                'source': self.source,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            rows.append(normalized_row)

        return rows

    def _normalize_stock_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        标准化股票数据为 symbol_master 格式

        Args:
            df: Tushare 返回的股票数据

        Returns:
            标准化后的数据列表
        """
        rows = []

        for _, row in df.iterrows():
            # 判断状态
            delist_date = self._convert_date(row.get('delist_date'))
            status = 'delisted' if delist_date else 'active'

            # 提取交易所
            ts_code = row['ts_code']
            exchange = ts_code.split('.')[-1] if '.' in ts_code else 'UNKNOWN'

            normalized_row = {
                'symbol': ts_code,
                'name': row['name'],
                'asset_type': 'STOCK',
                'exchange': exchange,
                'list_date': self._convert_date(row.get('list_date')),
                'delist_date': delist_date,
                'status': status,
                'fund_type': None,
                'source': self.source,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            rows.append(normalized_row)

        return rows

    def collect_etf_symbols(self, force: bool = False) -> int:
        """
        采集 ETF 列表

        Args:
            force: 是否强制刷新

        Returns:
            采集的记录数
        """
        logger.info("=" * 60)
        logger.info("开始采集 ETF 列表")
        logger.info("=" * 60)

        try:
            # 调用 Tushare 接口
            df = fetch_etf_basic(save_csv=False)

            if df is None or len(df) == 0:
                logger.warning("未获取到 ETF 数据")
                return 0

            logger.info(f"获取到 {len(df)} 个 ETF")

            # 数据标准化
            rows = self._normalize_etf_data(df)
            logger.info(f"标准化完成，共 {len(rows)} 条记录")

            # 统计状态
            active_count = sum(1 for r in rows if r['status'] == 'active')
            delisted_count = sum(1 for r in rows if r['status'] == 'delisted')
            logger.info(f"  活跃: {active_count} 个")
            logger.info(f"  退市: {delisted_count} 个")

            # 批量写入数据库
            self.client.insert_many('symbol_master', rows)
            logger.info(f"✓ 成功写入 {len(rows)} 条 ETF 数据")

            # 更新数据源状态
            self.client.update_source_status(
                source_name='tushare_etf',
                data_type='symbols',
                status='success',
                rows_processed=len(rows),
                metadata={'active': active_count, 'delisted': delisted_count}
            )

            return len(rows)

        except Exception as e:
            logger.error(f"采集 ETF 列表失败: {e}", exc_info=True)
            self.client.update_source_status(
                source_name='tushare_etf',
                data_type='symbols',
                status='failed',
                error_message=str(e)
            )
            raise

    def collect_index_symbols(self, force: bool = False) -> int:
        """
        采集指数列表

        Args:
            force: 是否强制刷新

        Returns:
            采集的记录数
        """
        logger.info("=" * 60)
        logger.info("开始采集指数列表")
        logger.info("=" * 60)

        try:
            # 调用 Tushare 接口
            pro = get_tushare_pro()
            df = pro.index_basic(market='SSE')  # 上交所指数
            df_sz = pro.index_basic(market='SZSE')  # 深交所指数
            df = pd.concat([df, df_sz], ignore_index=True)

            if df is None or len(df) == 0:
                logger.warning("未获取到指数数据")
                return 0

            logger.info(f"获取到 {len(df)} 个指数")

            # 数据标准化
            rows = self._normalize_index_data(df)
            logger.info(f"标准化完成，共 {len(rows)} 条记录")

            # 统计状态
            active_count = sum(1 for r in rows if r['status'] == 'active')
            delisted_count = sum(1 for r in rows if r['status'] == 'delisted')
            logger.info(f"  活跃: {active_count} 个")
            logger.info(f"  退市: {delisted_count} 个")

            # 批量写入数据库
            self.client.insert_many('symbol_master', rows)
            logger.info(f"✓ 成功写入 {len(rows)} 条指数数据")

            # 更新数据源状态
            self.client.update_source_status(
                source_name='tushare_index',
                data_type='symbols',
                status='success',
                rows_processed=len(rows),
                metadata={'active': active_count, 'delisted': delisted_count}
            )

            return len(rows)

        except Exception as e:
            logger.error(f"采集指数列表失败: {e}", exc_info=True)
            self.client.update_source_status(
                source_name='tushare_index',
                data_type='symbols',
                status='failed',
                error_message=str(e)
            )
            raise

    def collect_stock_symbols(self, force: bool = False) -> int:
        """
        采集股票列表（预留）

        Args:
            force: 是否强制刷新

        Returns:
            采集的记录数
        """
        logger.info("=" * 60)
        logger.info("开始采集股票列表")
        logger.info("=" * 60)

        try:
            # 调用 Tushare 接口
            pro = get_tushare_pro()
            df = pro.stock_basic(
                exchange='',
                list_status='L',  # L=上市 D=退市 P=暂停上市
                fields='ts_code,symbol,name,area,industry,list_date,delist_date'
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到股票数据")
                return 0

            logger.info(f"获取到 {len(df)} 只股票")

            # 数据标准化
            rows = self._normalize_stock_data(df)
            logger.info(f"标准化完成，共 {len(rows)} 条记录")

            # 统计状态
            active_count = sum(1 for r in rows if r['status'] == 'active')
            delisted_count = sum(1 for r in rows if r['status'] == 'delisted')
            logger.info(f"  活跃: {active_count} 只")
            logger.info(f"  退市: {delisted_count} 只")

            # 批量写入数据库
            self.client.insert_many('symbol_master', rows)
            logger.info(f"✓ 成功写入 {len(rows)} 条股票数据")

            # 更新数据源状态
            self.client.update_source_status(
                source_name='tushare_stock',
                data_type='symbols',
                status='success',
                rows_processed=len(rows),
                metadata={'active': active_count, 'delisted': delisted_count}
            )

            return len(rows)

        except Exception as e:
            logger.error(f"采集股票列表失败: {e}", exc_info=True)
            self.client.update_source_status(
                source_name='tushare_stock',
                data_type='symbols',
                status='failed',
                error_message=str(e)
            )
            raise

    def run(self, asset_type: str, force: bool = False) -> int:
        """
        执行采集任务

        Args:
            asset_type: 资产类型 ETF/INDEX/STOCK
            force: 是否强制刷新

        Returns:
            采集的记录数
        """
        # 记录任务开始
        self.job_id = self.client.write_job_run_log(
            job_name=f'collect_{asset_type.lower()}_symbols',
            source_name=f'tushare_{asset_type.lower()}',
            start_time=self.start_time,
            status='running',
            params={'asset_type': asset_type, 'force': force}
        )

        try:
            # 根据资产类型调用不同的采集方法
            if asset_type == 'ETF':
                count = self.collect_etf_symbols(force)
            elif asset_type == 'INDEX':
                count = self.collect_index_symbols(force)
            elif asset_type == 'STOCK':
                count = self.collect_stock_symbols(force)
            else:
                raise ValueError(f"不支持的资产类型: {asset_type}")

            # 记录任务成功
            self.client.write_job_run_log(
                job_name=f'collect_{asset_type.lower()}_symbols',
                source_name=f'tushare_{asset_type.lower()}',
                start_time=self.start_time,
                end_time=datetime.now(),
                status='success',
                rows_written=count,
                params={'asset_type': asset_type, 'force': force}
            )

            logger.info("=" * 60)
            logger.info(f"✓ 采集完成，共 {count} 条记录")
            logger.info("=" * 60)

            return count

        except Exception as e:
            # 记录任务失败
            self.client.write_job_run_log(
                job_name=f'collect_{asset_type.lower()}_symbols',
                source_name=f'tushare_{asset_type.lower()}',
                start_time=self.start_time,
                end_time=datetime.now(),
                status='failed',
                error_message=str(e),
                params={'asset_type': asset_type, 'force': force}
            )
            raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='采集证券主数据（ETF/指数/股票）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 采集 ETF 列表
  python scripts/collect_symbols.py --asset-type ETF

  # 采集指数列表
  python scripts/collect_symbols.py --asset-type INDEX

  # 采集股票列表
  python scripts/collect_symbols.py --asset-type STOCK

  # 强制刷新
  python scripts/collect_symbols.py --asset-type ETF --force
        """
    )

    parser.add_argument(
        '--asset-type',
        type=str,
        required=True,
        choices=['ETF', 'INDEX', 'STOCK'],
        help='资产类型'
    )

    parser.add_argument(
        '--source',
        type=str,
        default='tushare',
        help='数据源（默认: tushare）'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='强制刷新（忽略缓存）'
    )

    args = parser.parse_args()

    try:
        collector = SymbolCollector(source=args.source)
        count = collector.run(args.asset_type, args.force)

        logger.info(f"\n🎉 任务完成！共采集 {count} 条 {args.asset_type} 数据")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\n⚠ 用户中断")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n✗ 任务失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
