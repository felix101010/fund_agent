#!/usr/bin/env python3
"""
新闻采集脚本

使用方法：
    # 采集最近1天
    uv run python scripts/collect_news.py --days 1

    # 采集指定日期范围
    uv run python scripts/collect_news.py --start-date 2026-06-01 --end-date 2026-06-02

    # Dry-run模式（不写数据库）
    uv run python scripts/collect_news.py --days 1 --dry-run
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.data_sources.news.news_service import NewsCollectionService
from fund_quant.common.logger import logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='采集财经新闻',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 采集最近1天
  uv run python scripts/collect_news.py --days 1

  # 采集指定日期范围
  uv run python scripts/collect_news.py --start-date 2026-06-01 --end-date 2026-06-02

  # Dry-run模式（不写数据库）
  uv run python scripts/collect_news.py --days 1 --dry-run
        """
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='开始日期 YYYY-MM-DD'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='结束日期 YYYY-MM-DD'
    )

    parser.add_argument(
        '--days',
        type=int,
        help='采集最近N天'
    )

    parser.add_argument(
        '--sources',
        nargs='+',
        default=['cls'],
        help='数据源（目前只支持 cls）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry-run模式（不写入数据库）'
    )

    args = parser.parse_args()

    # 处理日期参数
    if args.days:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    else:
        start_date = args.start_date or (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')

    # 初始化ClickHouse客户端
    client = ClickHouseClient()

    try:
        # 初始化新闻采集服务
        service = NewsCollectionService(client)

        # 采集新闻
        df = service.collect_news(start_date, end_date, args.sources)

        if df.empty:
            logger.warning("\n✗ 未采集到新闻")
            return

        # 统计信息
        logger.info("\n" + "=" * 60)
        logger.info("采集统计")
        logger.info("=" * 60)
        logger.info(f"总数: {len(df)}")
        logger.info(f"\n来源分布:")
        for source, count in df['source'].value_counts().items():
            logger.info(f"  {source}: {count}")

        # 时间分布
        logger.info(f"\n时间范围:")
        logger.info(f"  最早: {df['publish_time'].min()}")
        logger.info(f"  最晚: {df['publish_time'].max()}")

        # 保存到数据库
        if args.dry_run:
            logger.info("\n" + "=" * 60)
            logger.info("✓ Dry-run模式，未写入数据库")
            logger.info("=" * 60)

            # 显示前5条预览
            logger.info("\n前5条预览:")
            for _, row in df.head(5).iterrows():
                logger.info(f"  [{row['publish_time']}] {row['title'][:50]}...")
        else:
            service.save_to_db(df)
            logger.info("\n" + "=" * 60)
            logger.info("✓ 新闻采集完成")
            logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("\n✗ 用户中断")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n✗ 任务失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
