#!/usr/bin/env python3
"""
主题强度查询工具

提供多种维度查看主题强度排名：
1. 按收益率排名（短期/中期/长期）
2. 按Alpha排名（相对沪深300超额收益）
3. 按成交额活跃度排名
4. 按趋势状态排名
5. 综合评分排名
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data.storage.clickhouse_client import ClickHouseClient


def get_latest_date(client: ClickHouseClient) -> str:
    """获取最新交易日期（选择有最多主题数据的日期）"""
    sql = """
    SELECT trade_date, COUNT(*) as theme_count
    FROM theme_daily_factors
    GROUP BY trade_date
    ORDER BY trade_date DESC
    LIMIT 10
    """
    df = client.query_df(sql)

    if df is None or len(df) == 0:
        return None

    # 找到主题数量最多的最新日期
    max_themes = df['theme_count'].max()
    latest_full_date = df[df['theme_count'] == max_themes].iloc[0]['trade_date']

    return latest_full_date.strftime('%Y-%m-%d')


def query_by_return(client: ClickHouseClient, period: str = '5d', date: str = None, limit: int = 10):
    """
    按收益率排名

    Args:
        period: '1d', '3d', '5d', '20d', '60d'
        date: 指定日期，None表示最新
        limit: 显示前N名
    """
    if date is None:
        date = get_latest_date(client)

    print(f"\n{'='*70}")
    print(f"📊 {period}收益率排名 (日期: {date})")
    print(f"{'='*70}")

    sql = f"""
    SELECT
        theme_name,
        index_close,
        ret_{period} as return_pct,
        hs300_ret_{period} as hs300_pct,
        alpha_{period} as alpha_pct,
        amount_ratio_5d,
        trend_score
    FROM theme_daily_factors
    WHERE trade_date = '{date}'
    ORDER BY ret_{period} DESC
    LIMIT {limit}
    """

    df = client.query_df(sql)

    if df is None or len(df) == 0:
        print("⚠ 无数据")
        return

    # 格式化输出
    print(f"\n{'排名':<4} {'主题':<12} {'收益率%':<10} {'沪深300%':<10} {'Alpha%':<10} {'成交倍数':<10} {'趋势分':<8}")
    print("-" * 70)

    for idx, row in df.iterrows():
        print(f"{idx+1:<4} {row['theme_name']:<12} "
              f"{row['return_pct']:>9.2f} {row['hs300_pct']:>9.2f} "
              f"{row['alpha_pct']:>9.2f} {row['amount_ratio_5d']:>9.2f} "
              f"{row['trend_score']:>8}")


def query_by_alpha(client: ClickHouseClient, period: str = '5d', date: str = None, limit: int = 10):
    """按Alpha排名（相对沪深300的超额收益）"""
    if date is None:
        date = get_latest_date(client)

    print(f"\n{'='*70}")
    print(f"🎯 {period} Alpha排名 - 相对沪深300超额收益 (日期: {date})")
    print(f"{'='*70}")

    sql = f"""
    SELECT
        theme_name,
        ret_{period} as return_pct,
        hs300_ret_{period} as hs300_pct,
        alpha_{period} as alpha_pct,
        trend_score
    FROM theme_daily_factors
    WHERE trade_date = '{date}'
    ORDER BY alpha_{period} DESC
    LIMIT {limit}
    """

    df = client.query_df(sql)

    if df is None or len(df) == 0:
        print("⚠ 无数据")
        return

    print(f"\n{'排名':<4} {'主题':<12} {'Alpha%':<10} {'主题收益%':<12} {'沪深300%':<10} {'趋势分':<8}")
    print("-" * 70)

    for idx, row in df.iterrows():
        print(f"{idx+1:<4} {row['theme_name']:<12} "
              f"{row['alpha_pct']:>9.2f} {row['return_pct']:>11.2f} "
              f"{row['hs300_pct']:>9.2f} {row['trend_score']:>8}")


def query_by_volume(client: ClickHouseClient, date: str = None, limit: int = 10):
    """按成交活跃度排名"""
    if date is None:
        date = get_latest_date(client)

    print(f"\n{'='*70}")
    print(f"💰 成交活跃度排名 (日期: {date})")
    print(f"{'='*70}")

    sql = f"""
    SELECT
        theme_name,
        etf_amount / 100000000 as amount_yi,
        amount_ratio_1d,
        amount_ratio_5d,
        ret_5d,
        trend_score
    FROM theme_daily_factors
    WHERE trade_date = '{date}'
    ORDER BY amount_ratio_5d DESC
    LIMIT {limit}
    """

    df = client.query_df(sql)

    if df is None or len(df) == 0:
        print("⚠ 无数据")
        return

    print(f"\n{'排名':<4} {'主题':<12} {'成交额(亿)':<12} {'1日倍数':<10} {'5日倍数':<10} {'5日涨跌%':<12} {'趋势分':<8}")
    print("-" * 70)

    for idx, row in df.iterrows():
        print(f"{idx+1:<4} {row['theme_name']:<12} "
              f"{row['amount_yi']:>11.2f} {row['amount_ratio_1d']:>9.2f} "
              f"{row['amount_ratio_5d']:>9.2f} {row['ret_5d']:>11.2f} "
              f"{row['trend_score']:>8}")


def query_by_trend(client: ClickHouseClient, date: str = None, limit: int = 10):
    """按趋势状态排名"""
    if date is None:
        date = get_latest_date(client)

    print(f"\n{'='*70}")
    print(f"📈 趋势状态排名 (日期: {date})")
    print(f"{'='*70}")

    sql = f"""
    SELECT
        theme_name,
        trend_score,
        above_ma20,
        above_ma60,
        ma5_gt_ma20,
        ma20_gt_ma60,
        ret_5d,
        alpha_5d
    FROM theme_daily_factors
    WHERE trade_date = '{date}'
    ORDER BY trend_score DESC, ret_5d DESC
    LIMIT {limit}
    """

    df = client.query_df(sql)

    if df is None or len(df) == 0:
        print("⚠ 无数据")
        return

    print(f"\n{'排名':<4} {'主题':<12} {'趋势分':<8} {'价>MA20':<8} {'价>MA60':<8} "
          f"{'MA5>20':<8} {'MA20>60':<8} {'5日涨跌%':<12} {'5日Alpha%':<12}")
    print("-" * 85)

    for idx, row in df.iterrows():
        above20 = '✓' if row['above_ma20'] else '✗'
        above60 = '✓' if row['above_ma60'] else '✗'
        ma5_20 = '✓' if row['ma5_gt_ma20'] else '✗'
        ma20_60 = '✓' if row['ma20_gt_ma60'] else '✗'

        print(f"{idx+1:<4} {row['theme_name']:<12} {row['trend_score']:>7} "
              f"{above20:>7} {above60:>7} {ma5_20:>7} {ma20_60:>7} "
              f"{row['ret_5d']:>11.2f} {row['alpha_5d']:>11.2f}")


def query_composite_score(client: ClickHouseClient, date: str = None, limit: int = 10):
    """
    综合评分排名

    评分规则：
    - 收益率得分（40%）：5日收益率标准化
    - Alpha得分（30%）：5日Alpha标准化
    - 活跃度得分（20%）：5日成交额倍数标准化
    - 趋势得分（10%）：趋势分/4
    """
    if date is None:
        date = get_latest_date(client)

    print(f"\n{'='*70}")
    print(f"🏆 综合强度排名 (日期: {date})")
    print(f"{'='*70}")
    print("评分规则: 收益率40% + Alpha30% + 活跃度20% + 趋势10%")

    sql = f"""
    SELECT
        theme_name,
        ret_5d,
        alpha_5d,
        amount_ratio_5d,
        trend_score,
        -- 归一化得分（0-100分）
        (ret_5d - min_ret) / nullif(max_ret - min_ret, 0) * 40 as ret_score,
        (alpha_5d - min_alpha) / nullif(max_alpha - min_alpha, 0) * 30 as alpha_score,
        (amount_ratio_5d - min_ratio) / nullif(max_ratio - min_ratio, 0) * 20 as volume_score,
        trend_score / 4.0 * 10 as trend_score_norm,
        -- 综合得分
        (ret_5d - min_ret) / nullif(max_ret - min_ret, 0) * 40 +
        (alpha_5d - min_alpha) / nullif(max_alpha - min_alpha, 0) * 30 +
        (amount_ratio_5d - min_ratio) / nullif(max_ratio - min_ratio, 0) * 20 +
        trend_score / 4.0 * 10 as composite_score
    FROM (
        SELECT
            *,
            MIN(ret_5d) OVER () as min_ret,
            MAX(ret_5d) OVER () as max_ret,
            MIN(alpha_5d) OVER () as min_alpha,
            MAX(alpha_5d) OVER () as max_alpha,
            MIN(amount_ratio_5d) OVER () as min_ratio,
            MAX(amount_ratio_5d) OVER () as max_ratio
        FROM theme_daily_factors
        WHERE trade_date = '{date}'
    )
    ORDER BY composite_score DESC
    LIMIT {limit}
    """

    df = client.query_df(sql)

    if df is None or len(df) == 0:
        print("⚠ 无数据")
        return

    print(f"\n{'排名':<4} {'主题':<12} {'综合分':<10} {'收益分':<10} {'Alpha分':<10} "
          f"{'活跃分':<10} {'趋势分':<10}")
    print("-" * 70)

    for idx, row in df.iterrows():
        print(f"{idx+1:<4} {row['theme_name']:<12} "
              f"{row['composite_score']:>9.1f} {row['ret_score']:>9.1f} "
              f"{row['alpha_score']:>9.1f} {row['volume_score']:>9.1f} "
              f"{row['trend_score_norm']:>9.1f}")


def query_theme_detail(client: ClickHouseClient, theme_name: str, days: int = 10):
    """查看单个主题的历史走势"""
    print(f"\n{'='*70}")
    print(f"📋 主题详情: {theme_name} (最近{days}天)")
    print(f"{'='*70}")

    sql = f"""
    SELECT
        trade_date,
        index_close,
        ret_1d,
        ret_5d,
        alpha_5d,
        amount_ratio_5d,
        trend_score
    FROM theme_daily_factors
    WHERE theme_name = '{theme_name}'
    ORDER BY trade_date DESC
    LIMIT {days}
    """

    df = client.query_df(sql)

    if df is None or len(df) == 0:
        print("⚠ 无数据")
        return

    print(f"\n{'日期':<12} {'指数点位':<12} {'1日%':<10} {'5日%':<10} {'5日Alpha%':<12} {'成交倍数':<10} {'趋势分':<8}")
    print("-" * 80)

    for _, row in df.iterrows():
        print(f"{row['trade_date'].strftime('%Y-%m-%d'):<12} "
              f"{row['index_close']:>11.2f} {row['ret_1d']:>9.2f} "
              f"{row['ret_5d']:>9.2f} {row['alpha_5d']:>11.2f} "
              f"{row['amount_ratio_5d']:>9.2f} {row['trend_score']:>8}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='主题强度查询工具')
    parser.add_argument('--mode', '-m', type=str, default='composite',
                       choices=['return', 'alpha', 'volume', 'trend', 'composite', 'detail'],
                       help='查询模式')
    parser.add_argument('--period', '-p', type=str, default='5d',
                       choices=['1d', '3d', '5d', '20d', '60d'],
                       help='周期（仅用于return/alpha模式）')
    parser.add_argument('--date', '-d', type=str, default=None,
                       help='指定日期 YYYY-MM-DD（默认最新）')
    parser.add_argument('--limit', '-l', type=int, default=10,
                       help='显示数量（默认10）')
    parser.add_argument('--theme', '-t', type=str, default=None,
                       help='主题名称（detail模式）')
    parser.add_argument('--days', type=int, default=10,
                       help='历史天数（detail模式）')

    args = parser.parse_args()

    # 初始化客户端
    client = ClickHouseClient()

    try:
        if args.mode == 'return':
            query_by_return(client, args.period, args.date, args.limit)
        elif args.mode == 'alpha':
            query_by_alpha(client, args.period, args.date, args.limit)
        elif args.mode == 'volume':
            query_by_volume(client, args.date, args.limit)
        elif args.mode == 'trend':
            query_by_trend(client, args.date, args.limit)
        elif args.mode == 'composite':
            query_composite_score(client, args.date, args.limit)
        elif args.mode == 'detail':
            if not args.theme:
                print("❌ detail模式需要指定主题名称，使用 --theme 参数")
                sys.exit(1)
            query_theme_detail(client, args.theme, args.days)

        print()

    except Exception as e:
        logger.error(f"查询失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
