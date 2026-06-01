#!/usr/bin/env python3
"""
采集主题ETF历史数据

从theme_etf_to_collect.csv读取ETF清单，批量采集历史数据到daily_bars表
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.market.tushare_provider import get_tushare_pro
from fund_quant.data.storage.clickhouse_client import ClickHouseClient


def collect_etf_data(
    etf_list: list,
    start_date: str = None,
    end_date: str = None,
    batch_size: int = 10
):
    """
    批量采集ETF历史数据

    Args:
        etf_list: ETF代码列表
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        batch_size: 每批采集数量
    """
    pro = get_tushare_pro()
    client = ClickHouseClient()

    # 默认采集最近1年数据
    if not end_date:
        end_date = datetime.now().strftime('%Y%m%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

    logger.info(f"开始采集 {len(etf_list)} 只ETF数据")
    logger.info(f"时间范围: {start_date} ~ {end_date}")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for i, etf_code in enumerate(etf_list, 1):
        try:
            # 检查是否已存在
            check_sql = f"""
            SELECT COUNT(*) as cnt
            FROM daily_bars
            WHERE symbol = '{etf_code}' AND asset_type = 'ETF'
            """
            result = client.query_df(check_sql)
            existing_count = result.iloc[0]['cnt']

            if existing_count > 0:
                logger.info(f"[{i}/{len(etf_list)}] {etf_code} - 已存在{existing_count}条数据，跳过")
                skip_count += 1
                continue

            # 采集数据
            logger.info(f"[{i}/{len(etf_list)}] {etf_code} - 开始采集...")
            df = pro.fund_daily(ts_code=etf_code, start_date=start_date, end_date=end_date)

            if df is None or len(df) == 0:
                logger.warning(f"[{i}/{len(etf_list)}] {etf_code} - 无数据")
                fail_count += 1
                continue

            # 转换为daily_bars格式
            df['symbol'] = df['ts_code']
            df['asset_type'] = 'ETF'
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df['source'] = 'tushare'
            df['adj_type'] = 'none'

            # 选择需要的字段（使用daily_bars表的实际字段名）
            columns = [
                'symbol', 'asset_type', 'trade_date',
                'open', 'high', 'low', 'close', 'pre_close',
                'change', 'pct_chg', 'vol', 'amount',
                'source', 'adj_type'
            ]

            # 重命名vol字段
            df = df.rename(columns={'vol': 'volume'})
            columns = [c if c != 'vol' else 'volume' for c in columns]

            df = df[columns]

            # 插入数据库
            rows = df.to_dict('records')
            client.insert_many('daily_bars', rows)

            logger.info(f"[{i}/{len(etf_list)}] {etf_code} - 成功采集{len(df)}条数据")
            success_count += 1

            # 每批次后暂停
            if i % batch_size == 0:
                logger.info(f"已完成 {i}/{len(etf_list)}，暂停1秒...")
                import time
                time.sleep(1)

        except Exception as e:
            logger.error(f"[{i}/{len(etf_list)}] {etf_code} - 采集失败: {e}")
            fail_count += 1
            continue

    logger.info("=" * 60)
    logger.info("采集完成")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  失败: {fail_count}")
    logger.info(f"  跳过: {skip_count}")
    logger.info(f"  总计: {len(etf_list)}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='采集主题ETF历史数据')
    parser.add_argument('--input', type=str,
                       default='data/processed/theme_etf_to_collect.csv',
                       help='ETF清单文件路径')
    parser.add_argument('--start-date', type=str,
                       help='开始日期 YYYYMMDD（默认1年前）')
    parser.add_argument('--end-date', type=str,
                       help='结束日期 YYYYMMDD（默认今天）')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='每批采集数量')

    args = parser.parse_args()

    # 读取ETF清单
    df = pd.read_csv(args.input)
    etf_list = df['etf_code'].unique().tolist()

    logger.info(f"从 {args.input} 读取到 {len(etf_list)} 只ETF")

    # 开始采集
    collect_etf_data(
        etf_list=etf_list,
        start_date=args.start_date,
        end_date=args.end_date,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
