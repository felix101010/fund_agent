#!/usr/bin/env python3
"""
采集主题指数历史数据

从configs/themes/theme_index_mapping.yaml读取22个主题指数，
通过Tushare采集日线数据并存入ClickHouse的daily_bars表。
"""

import sys
from pathlib import Path
from datetime import datetime
import time
import pandas as pd
import yaml
from loguru import logger

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.market.tushare_provider import get_tushare_pro
from fund_quant.data.storage.clickhouse_client import ClickHouseClient


def load_theme_indices() -> pd.DataFrame:
    """
    从配置文件加载主题指数列表

    Returns:
        DataFrame with columns: theme_id, theme_name, index_code, index_name
    """
    config_file = project_root / "configs" / "themes" / "theme_index_mapping.yaml"

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    indices = []
    for mapping in config['mappings']:
        indices.append({
            'theme_id': mapping['theme_id'],
            'theme_name': mapping['theme_name'],
            'index_code': mapping['primary_index']['code'],
            'index_name': mapping['primary_index']['name']
        })

    return pd.DataFrame(indices)


def load_market_indices() -> pd.DataFrame:
    """
    从配置文件加载宽基指数列表

    Returns:
        DataFrame with columns: index_code, index_name, role
    """
    config_file = project_root / "configs" / "market" / "market_indices.yaml"

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    indices = []
    # 加载宽基指数
    for idx in config['market_indices']['broad_market']:
        indices.append({
            'index_code': idx['symbol'],
            'index_name': idx['name'],
            'role': idx['role']
        })

    # 加载风格指数
    for idx in config['market_indices']['style_indices']:
        indices.append({
            'index_code': idx['symbol'],
            'index_name': idx['name'],
            'role': idx['role']
        })

    return pd.DataFrame(indices)


def collect_index_data(
    pro,
    client: ClickHouseClient,
    index_code: str,
    start_date: str = '20240101',
    end_date: str = None
) -> pd.DataFrame:
    """
    采集指数日线数据

    Args:
        pro: Tushare Pro API实例
        client: ClickHouse客户端
        index_code: 指数代码
        start_date: 起始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD（默认今天）

    Returns:
        DataFrame or None
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    try:
        # 调用Tushare接口
        df = pro.index_daily(
            ts_code=index_code,
            start_date=start_date,
            end_date=end_date
        )

        if df is None or len(df) == 0:
            return None

        # 转换格式
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

        # 重命名和选择列（与daily_bars表结构对齐）
        df = df.rename(columns={
            'ts_code': 'symbol',
            'vol': 'volume',  # 成交量（手）
            'amount': 'amount'  # 成交额（千元）
        })

        # 处理NaN值：用close价格填充open/high/low
        # 某些指数早期数据可能缺失OHLC字段
        if df['open'].isna().any() or df['high'].isna().any() or df['low'].isna().any():
            df['open'] = df['open'].fillna(df['close'])
            df['high'] = df['high'].fillna(df['close'])
            df['low'] = df['low'].fillna(df['close'])

        # 添加资产类型
        df['asset_type'] = 'INDEX'

        # 选择需要的列
        df = df[['trade_date', 'symbol', 'asset_type', 'open', 'high', 'low', 'close', 'volume', 'amount']]

        # 按日期升序排序
        df = df.sort_values('trade_date')

        return df

    except Exception as e:
        logger.error(f"采集失败: {e}")
        return None


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("主题指数数据采集")
    logger.info("=" * 60)

    # 1. 加载指数列表
    logger.info("\n步骤1: 加载主题指数配置")
    theme_indices_df = load_theme_indices()
    logger.info(f"✓ 加载了 {len(theme_indices_df)} 个主题指数")

    logger.info("\n步骤2: 加载宽基指数配置")
    market_indices_df = load_market_indices()
    logger.info(f"✓ 加载了 {len(market_indices_df)} 个宽基指数")

    # 2. 初始化客户端
    logger.info("\n步骤3: 初始化API和数据库")
    pro = get_tushare_pro()
    client = ClickHouseClient()

    # 3. 设置时间范围
    start_date = '20240101'
    end_date = datetime.now().strftime('%Y%m%d')
    logger.info(f"\n步骤4: 采集主题指数数据")
    logger.info(f"时间范围: {start_date} ~ {end_date}")
    logger.info("")

    # 4. 采集主题指数
    success_count = 0
    fail_count = 0
    skip_count = 0

    for idx, row in theme_indices_df.iterrows():
        theme_id = row['theme_id']
        theme_name = row['theme_name']
        index_code = row['index_code']
        index_name = row['index_name']

        logger.info(f"[{idx+1}/{len(theme_indices_df)}] {theme_name} - {index_code} ({index_name})")

        # 检查是否已存在数据
        check_sql = f"""
        SELECT COUNT(*) as cnt
        FROM daily_bars
        WHERE symbol = '{index_code}' AND asset_type = 'INDEX'
        """
        result = client.query_df(check_sql)
        existing_count = int(result['cnt'].iloc[0]) if result is not None and len(result) > 0 else 0

        if existing_count > 0:
            logger.info(f"  ✓ 已存在 {existing_count} 条数据，跳过")
            skip_count += 1
            continue

        # 采集数据
        logger.info(f"  → 开始采集...")
        df = collect_index_data(pro, client, index_code, start_date, end_date)

        if df is None or len(df) == 0:
            logger.error(f"  ✗ 采集失败或数据为空")
            fail_count += 1
            time.sleep(0.5)  # 失败也要延迟
            continue

        # 写入数据库
        try:
            records = df.to_dict('records')
            client.insert_many('daily_bars', records)
            logger.info(f"  ✓ 成功采集 {len(records)} 条数据")
            success_count += 1
        except Exception as e:
            logger.error(f"  ✗ 写入数据库失败: {e}")
            fail_count += 1

        # 延迟避免频率限制
        time.sleep(0.5)

        # 每10个暂停1秒
        if (idx + 1) % 10 == 0:
            logger.info(f"  已完成 {idx+1}/{len(theme_indices_df)}，暂停1秒...")
            time.sleep(1)

    # 5. 采集宽基指数
    logger.info(f"\n步骤5: 采集宽基指数数据")
    logger.info("")

    market_success = 0
    market_fail = 0
    market_skip = 0

    for idx, row in market_indices_df.iterrows():
        index_code = row['index_code']
        index_name = row['index_name']
        role = row['role']

        logger.info(f"[{idx+1}/{len(market_indices_df)}] {index_name} - {index_code} ({role})")

        # 检查是否已存在数据
        check_sql = f"""
        SELECT COUNT(*) as cnt
        FROM daily_bars
        WHERE symbol = '{index_code}' AND asset_type = 'INDEX'
        """
        result = client.query_df(check_sql)
        existing_count = int(result['cnt'].iloc[0]) if result is not None and len(result) > 0 else 0

        if existing_count > 0:
            logger.info(f"  ✓ 已存在 {existing_count} 条数据，跳过")
            market_skip += 1
            continue

        # 采集数据
        logger.info(f"  → 开始采集...")
        df = collect_index_data(pro, client, index_code, start_date, end_date)

        if df is None or len(df) == 0:
            logger.error(f"  ✗ 采集失败或数据为空")
            market_fail += 1
            time.sleep(0.5)
            continue

        # 写入数据库
        try:
            records = df.to_dict('records')
            client.insert_many('daily_bars', records)
            logger.info(f"  ✓ 成功采集 {len(records)} 条数据")
            market_success += 1
        except Exception as e:
            logger.error(f"  ✗ 写入数据库失败: {e}")
            market_fail += 1

        # 延迟避免频率限制
        time.sleep(0.5)

    # 6. 汇总统计
    logger.info("\n" + "=" * 60)
    logger.info("采集完成")
    logger.info("=" * 60)
    logger.info(f"主题指数:")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  失败: {fail_count}")
    logger.info(f"  跳过: {skip_count}")
    logger.info(f"  总计: {len(theme_indices_df)}")
    logger.info(f"\n宽基指数:")
    logger.info(f"  成功: {market_success}")
    logger.info(f"  失败: {market_fail}")
    logger.info(f"  跳过: {market_skip}")
    logger.info(f"  总计: {len(market_indices_df)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
