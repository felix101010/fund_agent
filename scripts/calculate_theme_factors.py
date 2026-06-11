#!/usr/bin/env python3
"""
主题日度因子计算脚本（重构版）

功能：
1. 从daily_bars读取主题指数、ETF、沪深300的历史数据
2. 计算每个主题每日的强度因子
3. 写入theme_daily_factors表

使用方法：
    # 计算所有历史数据
    uv run python scripts/calculate_theme_factors.py

    # 只计算最近30天
    uv run python scripts/calculate_theme_factors.py --days 30

    # 计算指定日期范围
    uv run python scripts/calculate_theme_factors.py --start-date 2026-01-01 --end-date 2026-06-01

    # 只计算指定主题
    uv run python scripts/calculate_theme_factors.py --theme ai --start-date 2026-01-01

    # Dry-run模式（不写入数据库，只验证计算结果）
    uv run python scripts/calculate_theme_factors.py --dry-run --days 30
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.factors import ThemeDailyFactorCalculator, load_theme_config
from fund_quant.common.logger import logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='计算主题日度因子',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 计算所有历史数据
  uv run python scripts/calculate_theme_factors.py

  # 只计算最近30天
  uv run python scripts/calculate_theme_factors.py --days 30

  # 计算指定日期范围
  uv run python scripts/calculate_theme_factors.py --start-date 2026-01-01 --end-date 2026-06-01

  # 只计算指定主题
  uv run python scripts/calculate_theme_factors.py --theme ai --start-date 2026-01-01

  # Dry-run模式（验证计算，不写入数据库）
  uv run python scripts/calculate_theme_factors.py --dry-run --days 10
        """
    )

    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='计算最近N天数据（默认全部）'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='开始日期 YYYY-MM-DD'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='结束日期 YYYY-MM-DD（默认今天）'
    )

    parser.add_argument(
        '--theme',
        type=str,
        help='只计算指定主题ID（例如: ai, semiconductor）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry-run模式：只计算不写入数据库'
    )

    args = parser.parse_args()

    # 处理日期参数
    start_date = args.start_date
    end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')

    # 如果指定了days，计算start_date
    if args.days:
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')

    # 初始化ClickHouse客户端
    client = ClickHouseClient()

    try:
        # 1. 加载主题配置
        config_path = project_root / "configs" / "themes" / "theme_etf_mapping.yaml"
        theme_config = load_theme_config(config_path)
        logger.info(f"✓ 加载配置: {len(theme_config)} 个主题")

        # 2. 初始化因子计算器
        calculator = ThemeDailyFactorCalculator(
            clickhouse_client=client,
            theme_config=theme_config,
            benchmark_symbol="000300.SH"
        )

        # 3. 计算因子
        theme_ids = [args.theme] if args.theme else None
        result_df = calculator.calculate(
            start_date=start_date,
            end_date=end_date,
            theme_ids=theme_ids
        )

        if result_df.empty:
            logger.error("✗ 没有计算出任何因子数据")
            sys.exit(1)

        # 4. Dry-run模式：显示统计信息并退出
        if args.dry_run:
            logger.info("\n" + "=" * 60)
            logger.info("DRY-RUN 模式 - 计算结果预览")
            logger.info("=" * 60)

            # 统计信息
            logger.info(f"\n计算主题数量: {result_df['theme_id'].nunique()}")
            logger.info(f"生成因子行数: {len(result_df)}")

            if len(result_df) > 0:
                logger.info(f"最新交易日: {result_df['trade_date'].max()}")

                # Top 10 ret_5d
                logger.info("\n--- Top 10 ret_5d (5日收益率) ---")
                top_ret = result_df.nlargest(10, 'ret_5d')[['trade_date', 'theme_name', 'ret_5d']]
                for _, row in top_ret.iterrows():
                    logger.info(f"  {row['trade_date']} {row['theme_name']:12s} {row['ret_5d']:6.2f}%")

                # Top 10 alpha_20d
                logger.info("\n--- Top 10 alpha_20d (20日超额收益) ---")
                top_alpha = result_df.nlargest(10, 'alpha_20d')[['trade_date', 'theme_name', 'alpha_20d']]
                for _, row in top_alpha.iterrows():
                    logger.info(f"  {row['trade_date']} {row['theme_name']:12s} {row['alpha_20d']:6.2f}%")

                # Top 10 amount_ratio_1d
                logger.info("\n--- Top 10 amount_ratio_1d (当日成交额倍数) ---")
                top_amount = result_df.nlargest(10, 'amount_ratio_1d')[['trade_date', 'theme_name', 'amount_ratio_1d']]
                for _, row in top_amount.iterrows():
                    logger.info(f"  {row['trade_date']} {row['theme_name']:12s} {row['amount_ratio_1d']:6.2f}x")

            logger.info("\n" + "=" * 60)
            logger.info("✓ Dry-run 完成（未写入数据库）")
            logger.info("=" * 60)
            return

        # 5. 写入数据库
        logger.info("\n步骤4: 写入数据库")

        # 转换日期格式
        result_df['trade_date'] = result_df['trade_date'].dt.date

        # 获取要更新的日期范围
        min_date = result_df['trade_date'].min()
        max_date = result_df['trade_date'].max()

        # 删除这个日期范围内的旧数据（避免重复）
        delete_sql = f"""
        DELETE FROM theme_daily_factors
        WHERE trade_date >= '{min_date}' AND trade_date <= '{max_date}'
        """

        if theme_ids:
            # 如果只计算了指定主题，只删除这些主题的数据
            theme_ids_str = "', '".join(theme_ids)
            delete_sql = f"""
            DELETE FROM theme_daily_factors
            WHERE trade_date >= '{min_date}' AND trade_date <= '{max_date}'
              AND theme_id IN ('{theme_ids_str}')
            """

        logger.info(f"✓ 清理旧数据: {min_date} ~ {max_date}")
        client.execute(delete_sql)

        # 转换为字典列表
        records = result_df.to_dict('records')

        # 批量插入
        client.insert_many('theme_daily_factors', records)

        logger.info(f"✓ 成功写入 {len(records)} 条记录到 theme_daily_factors 表")
        logger.info("\n✓ 计算完成")

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
