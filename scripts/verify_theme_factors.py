#!/usr/bin/env python3
"""
主题因子验证工具（TradingView风格）

功能：
1. 从 theme_daily_factors 和 daily_bars 表读取数据
2. 生成专业的 TradingView 风格验证图
3. 每个主题一张图，包含K线、均线、成交量、成交额倍数

使用方法：
    # 显示所有主题统计信息
    uv run python scripts/verify_theme_factors.py --stats-only

    # 绘制指定主题（使用theme_id）
    uv run python scripts/verify_theme_factors.py --theme ai

    # 绘制所有主题
    uv run python scripts/verify_theme_factors.py --all

    # 指定输出目录
    uv run python scripts/verify_theme_factors.py --theme chip --output-dir ./charts
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import mplfinance as mpf

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.common.logger import logger

# 默认输出目录
DEFAULT_OUTPUT_DIR = project_root / "data" / "charts"


def fetch_theme_config(client: ClickHouseClient) -> pd.DataFrame:
    """
    从数据库读取主题配置

    Returns:
        主题配置DataFrame
    """
    sql = """
    SELECT DISTINCT
        theme_id,
        theme_name,
        index_symbol,
        etf_symbol
    FROM theme_daily_factors
    ORDER BY theme_id
    """

    df = client.query_df(sql)
    return df


def fetch_theme_factors(
    client: ClickHouseClient,
    theme_id: str
) -> pd.DataFrame:
    """
    获取主题因子数据

    Args:
        client: ClickHouse客户端
        theme_id: 主题ID

    Returns:
        主题因子DataFrame
    """
    sql = f"""
    SELECT
        trade_date,
        theme_id,
        theme_name,
        index_symbol,
        etf_symbol,
        index_close,
        ret_1d,
        ret_5d,
        ret_20d,
        ret_60d,
        alpha_5d,
        alpha_20d,
        alpha_60d,
        amount_ratio_1d,
        amount_ratio_5d,
        trend_score,
        index_ma5,
        index_ma10,
        index_ma20,
        index_ma30,
        index_ma60,
        index_ma250
    FROM theme_daily_factors
    WHERE theme_id = '{theme_id}'
    ORDER BY trade_date
    """

    df = client.query_df(sql)

    if df is not None and len(df) > 0:
        df['trade_date'] = pd.to_datetime(df['trade_date'])

    return df


def fetch_index_bars(
    client: ClickHouseClient,
    index_symbol: str
) -> pd.DataFrame:
    """
    获取指数K线数据

    Args:
        client: ClickHouse客户端
        index_symbol: 指数代码

    Returns:
        K线数据DataFrame
    """
    sql = f"""
    SELECT
        trade_date,
        open,
        high,
        low,
        close,
        volume
    FROM daily_bars
    WHERE symbol = '{index_symbol}' AND asset_type = 'INDEX'
    ORDER BY trade_date
    """

    df = client.query_df(sql)

    if df is not None and len(df) > 0:
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        # 转换数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)

    return df


def create_theme_chart(
    client: ClickHouseClient,
    theme_id: str,
    output_dir: Path
):
    """
    生成单个主题的TradingView风格验证图

    Args:
        client: ClickHouse客户端
        theme_id: 主题ID
        output_dir: 输出目录
    """
    # 1. 获取主题因子数据
    factors_df = fetch_theme_factors(client, theme_id)

    if factors_df is None or len(factors_df) == 0:
        logger.warning(f"主题 {theme_id} 无因子数据")
        return

    # 获取主题信息
    theme_name = factors_df['theme_name'].iloc[0]
    index_symbol = factors_df['index_symbol'].iloc[0]
    etf_symbol = factors_df['etf_symbol'].iloc[0]

    logger.info(f"生成图表: {theme_name} ({theme_id})")

    # 2. 获取指数K线数据
    kline_df = fetch_index_bars(client, index_symbol)

    if kline_df is None or len(kline_df) == 0:
        logger.warning(f"  ✗ 指数 {index_symbol} 无K线数据")
        return

    # 3. 合并数据（按日期对齐）
    merged_df = kline_df.merge(
        factors_df[['trade_date', 'index_ma5', 'index_ma10', 'index_ma20',
                    'index_ma30', 'index_ma60', 'index_ma250', 'amount_ratio_1d',
                    'ret_5d', 'ret_20d', 'ret_60d', 'alpha_5d', 'alpha_20d',
                    'alpha_60d', 'trend_score']],
        on='trade_date',
        how='left'
    )

    # 设置索引为日期
    merged_df.set_index('trade_date', inplace=True)

    # 只保留有因子数据的行
    merged_df = merged_df.dropna(subset=['index_ma5'])

    if len(merged_df) == 0:
        logger.warning(f"  ✗ 合并后无数据")
        return

    # 4. 获取最新数据用于标题
    latest = merged_df.iloc[-1]
    latest_date = merged_df.index[-1].strftime('%Y-%m-%d')
    latest_close = latest['close']
    latest_ret_5d = latest['ret_5d']
    latest_ret_20d = latest['ret_20d']
    latest_ret_60d = latest['ret_60d']
    latest_alpha_5d = latest['alpha_5d']
    latest_alpha_20d = latest['alpha_20d']
    latest_alpha_60d = latest['alpha_60d']
    latest_trend = int(latest['trend_score'])

    # 5. 准备均线数据
    apds = []

    # MA5 - 橙色
    apds.append(mpf.make_addplot(merged_df['index_ma5'], panel=0, color='#FF6B35',
                                   width=1.2, alpha=0.9, secondary_y=False))

    # MA10 - 蓝色
    apds.append(mpf.make_addplot(merged_df['index_ma10'], panel=0, color='#4ECDC4',
                                   width=1.2, alpha=0.9, secondary_y=False))

    # MA20 - 紫色
    apds.append(mpf.make_addplot(merged_df['index_ma20'], panel=0, color='#9D50BB',
                                   width=1.5, alpha=0.9, secondary_y=False))

    # MA30 - 绿色
    apds.append(mpf.make_addplot(merged_df['index_ma30'], panel=0, color='#26A69A',
                                   width=1.2, alpha=0.8, secondary_y=False))

    # MA60 - 黄色
    apds.append(mpf.make_addplot(merged_df['index_ma60'], panel=0, color='#FFD93D',
                                   width=1.5, alpha=0.9, secondary_y=False))

    # MA250 - 灰色
    apds.append(mpf.make_addplot(merged_df['index_ma250'], panel=0, color='#95A5A6',
                                   width=1.8, alpha=0.7, secondary_y=False))

    # 6. 成交额倍数（panel=2）
    apds.append(mpf.make_addplot(merged_df['amount_ratio_1d'], panel=2, color='#E74C3C',
                                   width=1.5, alpha=0.8, ylabel='成交额倍数'))

    # 7. 自定义样式
    mc = mpf.make_marketcolors(
        up='#EF5350',      # 涨-红色
        down='#26A69A',    # 跌-绿色
        edge='inherit',
        wick='inherit',
        volume='inherit',
        alpha=0.9
    )

    style = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle='-',
        gridcolor='#E0E0E0',
        gridaxis='both',
        facecolor='#FFFFFF',
        figcolor='#FFFFFF',
        y_on_right=False
    )

    # 8. 构建图表标题
    title_lines = [
        f"{theme_name} ({theme_id})  指数: {index_symbol}  ETF: {etf_symbol}",
        f"最新 ({latest_date}): 收盘={latest_close:.2f}  ret5d={latest_ret_5d:.2f}%  ret20d={latest_ret_20d:.2f}%  ret60d={latest_ret_60d:.2f}%",
        f"Alpha: 5d={latest_alpha_5d:.2f}%  20d={latest_alpha_20d:.2f}%  60d={latest_alpha_60d:.2f}%  趋势得分={latest_trend}/4"
    ]
    title = '\n'.join(title_lines)

    # 9. 绘制图表
    fig, axes = mpf.plot(
        merged_df,
        type='candle',
        style=style,
        addplot=apds,
        volume=True,
        volume_panel=1,
        panel_ratios=(4, 1, 1),  # K线:成交量:成交额倍数 = 4:1:1
        figsize=(18, 10),
        title=title,
        ylabel='价格',
        ylabel_lower='成交量',
        returnfig=True,
        datetime_format='%Y-%m',
        xrotation=0,
        tight_layout=True
    )

    # 10. 在成交额倍数面板添加基准线
    ax_amount = axes[3]  # panel=2 对应 axes[3] (0=K线, 1=成交量, 2=空, 3=成交额)
    ax_amount.axhline(y=1.0, color='#95A5A6', linestyle='--', linewidth=1, alpha=0.7, label='1.0')
    ax_amount.axhline(y=1.5, color='#F39C12', linestyle='--', linewidth=1, alpha=0.7, label='1.5')
    ax_amount.axhline(y=2.0, color='#E74C3C', linestyle='--', linewidth=1, alpha=0.7, label='2.0')
    ax_amount.legend(loc='upper right', fontsize=8)

    # 11. 在K线面板添加均线图例
    ax_kline = axes[0]
    legend_elements = [
        plt.Line2D([0], [0], color='#FF6B35', linewidth=2, label='MA5'),
        plt.Line2D([0], [0], color='#4ECDC4', linewidth=2, label='MA10'),
        plt.Line2D([0], [0], color='#9D50BB', linewidth=2, label='MA20'),
        plt.Line2D([0], [0], color='#26A69A', linewidth=2, label='MA30'),
        plt.Line2D([0], [0], color='#FFD93D', linewidth=2, label='MA60'),
        plt.Line2D([0], [0], color='#95A5A6', linewidth=2, label='MA250'),
    ]
    ax_kline.legend(handles=legend_elements, loc='upper left', fontsize=9, ncol=6)

    # 12. 保存图片
    output_file = output_dir / f"{theme_id}.png"
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close(fig)

    logger.info(f"  ✓ 已保存 {output_file}")


def print_statistics(client: ClickHouseClient):
    """
    打印主题统计信息

    Args:
        client: ClickHouse客户端
    """
    sql = """
    SELECT
        COUNT(*) as total_records,
        COUNT(DISTINCT theme_id) as theme_count,
        MIN(trade_date) as min_date,
        MAX(trade_date) as max_date
    FROM theme_daily_factors
    """

    stats = client.query_df(sql)

    if stats is None or len(stats) == 0:
        logger.error("无法获取统计信息")
        return

    logger.info("=" * 70)
    logger.info("主题因子数据统计")
    logger.info("=" * 70)
    logger.info(f"总记录数: {stats['total_records'].iloc[0]}")
    logger.info(f"主题数量: {stats['theme_count'].iloc[0]}")
    logger.info(f"日期范围: {stats['min_date'].iloc[0]} ~ {stats['max_date'].iloc[0]}")

    # 主题列表
    themes_sql = """
    SELECT DISTINCT
        theme_id,
        theme_name,
        index_symbol,
        COUNT(*) as record_count
    FROM theme_daily_factors
    GROUP BY theme_id, theme_name, index_symbol
    ORDER BY theme_id
    """

    themes = client.query_df(themes_sql)

    logger.info("\n主题列表:")
    for _, row in themes.iterrows():
        logger.info(f"  {row['theme_id']:15s} {row['theme_name']:12s} {row['index_symbol']:15s} {int(row['record_count']):4d} 行")

    logger.info("=" * 70)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='生成主题因子验证图（TradingView风格）',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--theme',
        type=str,
        help='指定主题ID（例如: ai, chip, semiconductor）'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='绘制所有主题'
    )

    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='只显示统计信息，不绘图'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        help='图表输出目录（默认: data/charts）'
    )

    args = parser.parse_args()

    # 设置输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = DEFAULT_OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    # 初始化ClickHouse客户端
    client = ClickHouseClient()

    try:
        # 1. 显示统计信息
        if args.stats_only or (not args.theme and not args.all):
            print_statistics(client)

            if not args.theme and not args.all:
                logger.info("\n提示: 使用以下命令绘制图表:")
                logger.info("  --theme ai             # 绘制指定主题")
                logger.info("  --all                  # 绘制所有主题")
                logger.info(f"\n图表保存位置: {output_dir.absolute()}")
            return

        # 2. 获取主题配置
        theme_config = fetch_theme_config(client)

        if theme_config is None or len(theme_config) == 0:
            logger.error("✗ 无法获取主题配置")
            sys.exit(1)

        # 3. 绘制图表
        if args.theme:
            # 绘制指定主题
            theme_exists = theme_config[theme_config['theme_id'] == args.theme]
            if len(theme_exists) == 0:
                logger.error(f"✗ 主题 '{args.theme}' 不存在")
                logger.info(f"可用主题: {', '.join(theme_config['theme_id'].tolist())}")
                sys.exit(1)

            create_theme_chart(client, args.theme, output_dir)
            logger.info(f"\n✓ 图表已保存到: {output_dir.absolute()}")

        elif args.all:
            # 绘制所有主题
            theme_ids = theme_config['theme_id'].tolist()
            logger.info(f"准备绘制 {len(theme_ids)} 个主题...\n")

            for i, theme_id in enumerate(theme_ids, 1):
                logger.info(f"[{i}/{len(theme_ids)}]")
                try:
                    create_theme_chart(client, theme_id, output_dir)
                except Exception as e:
                    logger.error(f"  ✗ 绘制失败: {e}")

            logger.info(f"\n✓ 已绘制所有主题")
            logger.info(f"✓ 图表已保存到: {output_dir.absolute()}")

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
