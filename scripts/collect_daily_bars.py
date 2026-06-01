#!/usr/bin/env python
"""
日线行情数据采集脚本
支持P0/P1优先级、主题采集、增量更新、断点续采
"""
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import yaml

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.market.tushare_provider import get_tushare_pro
from fund_quant.data.storage import ClickHouseClient
from fund_quant.data_sources.tushare.rate_limiter import RateLimiter
from fund_quant.data_sources.tushare.retry_policy import RetryPolicy
from fund_quant.common.logger import logger


class UniverseLoader:
    """标的池加载器"""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir

    def load_p0_symbols(self) -> List[Dict[str, Any]]:
        """加载P0核心标的池"""
        config_path = self.config_dir / "universe" / "p0_core.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config['symbols']

    def load_theme_config(self) -> Dict[str, Any]:
        """加载主题配置"""
        config_path = self.config_dir / "themes" / "theme_universe.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return {theme['theme_id']: theme for theme in config['themes']}


class DataQualityChecker:
    """数据质量检查器"""

    @staticmethod
    def check_ohlc_consistency(df: pd.DataFrame) -> Dict[str, Any]:
        """
        检查OHLC数据一致性

        Returns:
            检查结果字典
        """
        issues = []
        total_rows = len(df)

        if total_rows == 0:
            return {'valid': True, 'issues': [], 'total_rows': 0}

        # 检查1: high >= low
        invalid_hl = df[df['high'] < df['low']]
        if len(invalid_hl) > 0:
            issues.append(f"high < low: {len(invalid_hl)}条")

        # 检查2: high >= open, close
        invalid_h_open = df[df['high'] < df['open']]
        if len(invalid_h_open) > 0:
            issues.append(f"high < open: {len(invalid_h_open)}条")

        invalid_h_close = df[df['high'] < df['close']]
        if len(invalid_h_close) > 0:
            issues.append(f"high < close: {len(invalid_h_close)}条")

        # 检查3: low <= open, close
        invalid_l_open = df[df['low'] > df['open']]
        if len(invalid_l_open) > 0:
            issues.append(f"low > open: {len(invalid_l_open)}条")

        invalid_l_close = df[df['low'] > df['close']]
        if len(invalid_l_close) > 0:
            issues.append(f"low > close: {len(invalid_l_close)}条")

        # 检查4: 价格为0或负数
        invalid_price = df[(df['open'] <= 0) | (df['high'] <= 0) | (df['low'] <= 0) | (df['close'] <= 0)]
        if len(invalid_price) > 0:
            issues.append(f"价格<=0: {len(invalid_price)}条")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'total_rows': total_rows,
            'invalid_rows': len(invalid_hl) + len(invalid_h_open) + len(invalid_h_close) +
                           len(invalid_l_open) + len(invalid_l_close) + len(invalid_price)
        }

    @staticmethod
    def check_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
        """检查重复数据"""
        duplicates = df[df.duplicated(subset=['ts_code', 'trade_date'], keep=False)]
        return {
            'has_duplicates': len(duplicates) > 0,
            'duplicate_count': len(duplicates),
            'duplicate_dates': duplicates['trade_date'].unique().tolist() if len(duplicates) > 0 else []
        }


class DailyBarCollector:
    """日线行情采集器"""

    def __init__(self, dry_run: bool = False):
        """
        初始化采集器

        Args:
            dry_run: 是否为演练模式（不写入数据库）
        """
        self.dry_run = dry_run
        self.client = ClickHouseClient()
        self.rate_limiter = RateLimiter()
        self.retry_policy = RetryPolicy()
        self.quality_checker = DataQualityChecker()

        # 统计信息
        self.stats = {
            'total_symbols': 0,
            'success_symbols': 0,
            'failed_symbols': 0,
            'total_bars': 0,
            'skipped_symbols': 0,
            'start_time': datetime.now()
        }

        logger.info("=" * 60)
        logger.info("日线行情采集器初始化")
        logger.info("=" * 60)
        logger.info(f"演练模式: {'是' if dry_run else '否'}")

    def get_checkpoint_date(self, symbol: str, asset_type: str) -> Optional[str]:
        """
        获取断点日期（最后采集日期）

        Args:
            symbol: 证券代码
            asset_type: 资产类型

        Returns:
            最后交易日期（YYYYMMDD格式）或None
        """
        latest_date = self.client.get_latest_trade_date(symbol, asset_type)
        if latest_date:
            logger.debug(f"  断点: {symbol} 最后日期 {latest_date}")
        return latest_date

    def fetch_daily_bars(
        self,
        symbol: str,
        asset_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取日线行情数据（带限速和重试）

        Args:
            symbol: 证券代码
            asset_type: 资产类型
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            日线数据DataFrame或None
        """
        def _fetch():
            # 限速等待
            wait_time = self.rate_limiter.wait()
            if wait_time > 0:
                logger.debug(f"  限速等待: {wait_time:.3f}秒")

            # 调用API
            pro = get_tushare_pro()
            request_start = time.time()

            if asset_type == 'ETF':
                df = pro.fund_daily(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
                )
            elif asset_type == 'INDEX':
                df = pro.index_daily(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
                )
            elif asset_type == 'STOCK':
                df = pro.daily(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
                )
            else:
                raise ValueError(f"不支持的资产类型: {asset_type}")

            request_time = time.time() - request_start
            logger.debug(f"  API响应时间: {request_time:.3f}秒")

            return df

        # 使用重试策略执行
        try:
            df = self.retry_policy.execute(_fetch)
            return df
        except Exception as e:
            logger.error(f"  获取失败: {e}")
            return None

    def normalize_bars(self, df: pd.DataFrame, symbol: str, asset_type: str) -> List[Dict[str, Any]]:
        """
        标准化行情数据

        Args:
            df: 原始数据
            symbol: 证券代码
            asset_type: 资产类型

        Returns:
            标准化后的数据列表
        """
        rows = []

        for _, row in df.iterrows():
            # 转换日期
            trade_date_str = str(row['trade_date'])
            trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()

            normalized_row = {
                'symbol': symbol,
                'asset_type': asset_type,
                'trade_date': trade_date,
                'open': float(row['open']) if pd.notna(row['open']) else 0.0,
                'high': float(row['high']) if pd.notna(row['high']) else 0.0,
                'low': float(row['low']) if pd.notna(row['low']) else 0.0,
                'close': float(row['close']) if pd.notna(row['close']) else 0.0,
                'pre_close': float(row['pre_close']) if pd.notna(row['pre_close']) else 0.0,
                'change': float(row['change']) if pd.notna(row['change']) else 0.0,
                'pct_chg': float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0,
                'volume': float(row['vol']) if pd.notna(row['vol']) else 0.0,
                'amount': float(row['amount']) if pd.notna(row['amount']) else 0.0,
                'source': 'tushare',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            rows.append(normalized_row)

        return rows

    def collect_symbol(
        self,
        symbol: str,
        asset_type: str,
        priority: str,
        theme: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        incremental: bool = True
    ) -> Dict[str, Any]:
        """
        采集单个证券的日线数据

        Args:
            symbol: 证券代码
            asset_type: 资产类型
            priority: 优先级
            theme: 主题
            start_date: 开始日期
            end_date: 结束日期
            incremental: 是否增量更新

        Returns:
            采集结果
        """
        logger.info(f"采集: {symbol} ({asset_type}, {theme})")

        result = {
            'symbol': symbol,
            'asset_type': asset_type,
            'status': 'failed',
            'bars_count': 0,
            'error': None
        }

        try:
            # 1. 检查数据库最新日期
            checkpoint = self.get_checkpoint_date(symbol, asset_type)

            if checkpoint:
                logger.info(f"  数据库最新日期: {checkpoint}")
            else:
                logger.info(f"  数据库: 无数据")

            # 2. 判断是否需要采集
            actual_start_date = start_date

            if incremental and checkpoint:
                # 增量模式：从断点的下一天开始
                checkpoint_date = datetime.strptime(checkpoint, '%Y%m%d')
                next_date = checkpoint_date + timedelta(days=1)
                actual_start_date = next_date.strftime('%Y%m%d')

                logger.info(f"  目标结束日期: {end_date or '最新'}")

                # 如果断点日期已经 >= 结束日期，跳过
                if end_date and checkpoint >= end_date:
                    logger.info(f"  无需更新: 数据已是最新")
                    logger.info(f"  SKIPPED")
                    result['status'] = 'skipped'
                    self.stats['skipped_symbols'] += 1
                    return result

                logger.info(f"  增量采集: 从 {actual_start_date} 开始")

            # 3. 获取数据
            logger.info(f"  请求Tushare: {actual_start_date or '最早'} ~ {end_date or '最新'}")
            df = self.fetch_daily_bars(symbol, asset_type, actual_start_date, end_date)

            if df is None or len(df) == 0:
                logger.warning(f"  无数据返回")
                result['error'] = 'no_data'
                return result

            logger.info(f"  获取: {len(df)} 条")

            # 3. 数据质量检查
            quality_result = self.quality_checker.check_ohlc_consistency(df)
            if not quality_result['valid']:
                logger.warning(f"  数据质量问题: {', '.join(quality_result['issues'])}")

            dup_result = self.quality_checker.check_duplicates(df)
            if dup_result['has_duplicates']:
                logger.warning(f"  发现重复数据: {dup_result['duplicate_count']}条")

            # 4. 标准化数据
            rows = self.normalize_bars(df, symbol, asset_type)

            # 5. 写入数据库
            if not self.dry_run:
                self.client.insert_many('daily_bars', rows)
                logger.info(f"  ✓ 写入: {len(rows)} 条")
            else:
                logger.info(f"  [演练] 跳过写入: {len(rows)} 条")

            result['status'] = 'success'
            result['bars_count'] = len(rows)
            self.stats['total_bars'] += len(rows)
            self.stats['success_symbols'] += 1

            return result

        except Exception as e:
            logger.error(f"  ✗ 采集失败: {e}")
            result['error'] = str(e)
            self.stats['failed_symbols'] += 1
            return result

    def collect_universe(
        self,
        symbols: List[Dict[str, Any]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        incremental: bool = True
    ):
        """
        采集标的池

        Args:
            symbols: 标的列表
            start_date: 开始日期
            end_date: 结束日期
            incremental: 是否增量更新
        """
        self.stats['total_symbols'] = len(symbols)

        logger.info("=" * 60)
        logger.info(f"开始采集: {len(symbols)} 个标的")
        logger.info(f"日期范围: {start_date or '最早'} ~ {end_date or '最新'}")
        logger.info(f"增量模式: {'是' if incremental else '否'}")
        logger.info("=" * 60)

        for i, symbol_info in enumerate(symbols, 1):
            symbol = symbol_info['symbol']
            asset_type = symbol_info['asset_type']
            theme = symbol_info.get('theme', 'unknown')
            priority = 'P0'  # 默认P0

            logger.info(f"\n[{i}/{len(symbols)}] {symbol}")

            result = self.collect_symbol(
                symbol=symbol,
                asset_type=asset_type,
                priority=priority,
                theme=theme,
                start_date=start_date,
                end_date=end_date,
                incremental=incremental
            )

            # 短暂休息，避免过于密集
            if i < len(symbols):
                time.sleep(0.1)

    def print_summary(self):
        """输出采集总结"""
        end_time = datetime.now()
        duration = (end_time - self.stats['start_time']).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("采集总结")
        logger.info("=" * 60)
        logger.info(f"总标的数: {self.stats['total_symbols']}")
        logger.info(f"成功: {self.stats['success_symbols']}")
        logger.info(f"失败: {self.stats['failed_symbols']}")
        logger.info(f"跳过: {self.stats['skipped_symbols']}")
        logger.info(f"总行情条数: {self.stats['total_bars']}")
        logger.info(f"总耗时: {duration:.1f}秒")
        logger.info("=" * 60)

        # 限速器统计
        self.rate_limiter.log_stats()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='采集日线行情数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # P0核心标的池（增量）
  python scripts/collect_daily_bars.py --priority P0 --incremental

  # P0核心标的池（全量，最近3年）
  python scripts/collect_daily_bars.py --priority P0 --start 20210101 --end 20241231

  # 单个标的
  python scripts/collect_daily_bars.py --symbol 510300.SH --asset-type ETF

  # 演练模式
  python scripts/collect_daily_bars.py --priority P0 --dry-run
        """
    )

    parser.add_argument('--priority', type=str, choices=['P0', 'P1', 'P2'], help='优先级')
    parser.add_argument('--theme', type=str, help='主题ID')
    parser.add_argument('--symbol', type=str, help='单个证券代码')
    parser.add_argument('--asset-type', type=str, choices=['ETF', 'INDEX', 'STOCK'], help='资产类型（与--symbol配合使用）')
    parser.add_argument('--start', type=str, help='开始日期 YYYYMMDD')
    parser.add_argument('--end', type=str, help='结束日期 YYYYMMDD')
    parser.add_argument('--incremental', action='store_true', help='增量更新（从最后日期继续）')
    parser.add_argument('--dry-run', action='store_true', help='演练模式（不写入数据库）')

    args = parser.parse_args()

    try:
        # 初始化采集器
        collector = DailyBarCollector(dry_run=args.dry_run)

        # 加载配置
        config_dir = Path(__file__).parent.parent / "configs"
        loader = UniverseLoader(config_dir)

        # 确定采集范围
        symbols = []

        if args.symbol:
            # 单个标的
            if not args.asset_type:
                logger.error("使用 --symbol 时必须指定 --asset-type")
                sys.exit(1)

            symbols = [{
                'symbol': args.symbol,
                'asset_type': args.asset_type,
                'theme': 'manual',
                'role': 'manual'
            }]

        elif args.priority == 'P0':
            # P0核心标的池
            symbols = loader.load_p0_symbols()

        else:
            logger.error("请指定 --priority P0 或 --symbol")
            sys.exit(1)

        # 执行采集
        collector.collect_universe(
            symbols=symbols,
            start_date=args.start,
            end_date=args.end,
            incremental=args.incremental
        )

        # 输出总结
        collector.print_summary()

        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\n⚠ 用户中断")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n✗ 任务失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
