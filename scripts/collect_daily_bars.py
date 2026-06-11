#!/usr/bin/env python3
"""
日线行情数据采集命令入口
仅负责命令行参数解析，核心逻辑在 market/bars 模块中
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.market.bars import DailyBarService
from fund_quant.common.logger import logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='日线行情数据采集',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 采集所有数据（主题指数 + 宽基指数 + 主题ETF）
  uv run python scripts/collect_daily_bars.py --type all

  # 只采集主题指数
  uv run python scripts/collect_daily_bars.py --type theme_index

  # 只采集主题ETF
  uv run python scripts/collect_daily_bars.py --type theme_etf

  # 只采集宽基指数
  uv run python scripts/collect_daily_bars.py --type market_index

  # 指定日期范围
  uv run python scripts/collect_daily_bars.py --type all --start-date 20260101 --end-date 20260601

  # 增量更新（从最后日期继续）
  uv run python scripts/collect_daily_bars.py --type all --incremental
        """
    )

    parser.add_argument(
        '--type',
        type=str,
        required=True,
        choices=['all', 'theme_index', 'theme_etf', 'market_index'],
        help='采集类型'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='开始日期 YYYYMMDD（默认1年前）'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='结束日期 YYYYMMDD（默认今天）'
    )

    parser.add_argument(
        '--incremental',
        action='store_true',
        help='增量更新模式（从最后日期继续）'
    )

    parser.add_argument(
        '--config-dir',
        type=str,
        help='配置文件目录路径（默认为项目根目录/configs）'
    )

    args = parser.parse_args()

    # 处理日期参数
    start_date = args.start_date
    end_date = args.end_date or datetime.now().strftime('%Y%m%d')

    # 如果未指定开始日期且非增量模式，默认采集1年数据
    if not start_date and not args.incremental:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

    # 初始化服务
    config_dir = Path(args.config_dir) if args.config_dir else None
    service = DailyBarService(config_dir=config_dir)

    try:
        # 根据类型执行采集
        if args.type == 'all':
            service.collect_all(start_date, end_date, args.incremental)

        elif args.type == 'theme_index':
            service.collect_theme_indices(start_date, end_date, args.incremental)

        elif args.type == 'theme_etf':
            service.collect_theme_etfs(start_date, end_date, args.incremental)

        elif args.type == 'market_index':
            service.collect_market_indices(start_date, end_date, args.incremental)

        logger.info("\n✓ 采集任务完成")

    except KeyboardInterrupt:
        logger.warning("\n✗ 用户中断")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n✗ 采集失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
