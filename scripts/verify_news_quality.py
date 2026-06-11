#!/usr/bin/env python3
"""
验证采集数据的实时性和准确性
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.common.logger import logger


def main():
    """验证采集数据"""
    client = ClickHouseClient()

    logger.info("=" * 80)
    logger.info("验证华尔街见闻采集数据的实时性和准确性")
    logger.info("=" * 80)

    # 1. 查看最新5条新闻
    logger.info("\n【1. 最新5条新闻】")
    sql = """
    SELECT
        news_id,
        title,
        publish_time,
        first_seen_time,
        delay_seconds,
        url
    FROM raw_news
    WHERE source = 'wallstreetcn'
    ORDER BY publish_time DESC
    LIMIT 5
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        for idx, row in df.iterrows():
            logger.info(f"\n{idx + 1}. {row['title'][:60]}...")
            logger.info(f"   发布时间: {row['publish_time']}")
            logger.info(f"   采集时间: {row['first_seen_time']}")
            logger.info(f"   采集延迟: {row['delay_seconds']}秒 ({row['delay_seconds'] // 60}分钟)")
            logger.info(f"   链接: {row['url']}")

    # 2. 统计延迟分布
    logger.info("\n【2. 采集延迟统计】")
    sql = """
    SELECT
        count() as total,
        min(delay_seconds) as min_delay,
        max(delay_seconds) as max_delay,
        avg(delay_seconds) as avg_delay,
        quantile(0.5)(delay_seconds) as median_delay
    FROM raw_news
    WHERE source = 'wallstreetcn'
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        row = df.iloc[0]
        logger.info(f"  总数: {row['total']}")
        logger.info(f"  最小延迟: {row['min_delay']}秒 ({row['min_delay'] // 60}分钟)")
        logger.info(f"  最大延迟: {row['max_delay']}秒 ({row['max_delay'] // 60}分钟)")
        logger.info(f"  平均延迟: {row['avg_delay']:.0f}秒 ({row['avg_delay'] // 60:.0f}分钟)")
        logger.info(f"  中位延迟: {row['median_delay']:.0f}秒 ({row['median_delay'] // 60:.0f}分钟)")

    # 3. 时间分布
    logger.info("\n【3. 新闻时间分布】")
    sql = """
    SELECT
        toStartOfHour(publish_time) as hour,
        count() as cnt
    FROM raw_news
    WHERE source = 'wallstreetcn'
    GROUP BY hour
    ORDER BY hour DESC
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        for _, row in df.iterrows():
            logger.info(f"  {row['hour']}: {row['cnt']}条")

    # 4. 内容完整性检查
    logger.info("\n【4. 内容完整性检查】")
    sql = """
    SELECT
        count() as total,
        countIf(title = '') as empty_title,
        countIf(content = '') as empty_content,
        countIf(url = '') as empty_url,
        countIf(length(content) < 50) as short_content
    FROM raw_news
    WHERE source = 'wallstreetcn'
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        row = df.iloc[0]
        logger.info(f"  总数: {row['total']}")
        logger.info(f"  空标题: {row['empty_title']}")
        logger.info(f"  空内容: {row['empty_content']}")
        logger.info(f"  空链接: {row['empty_url']}")
        logger.info(f"  内容过短(<50字): {row['short_content']}")

    # 5. 对比RSSHub实时数据
    logger.info("\n【5. 对比RSSHub实时数据】")
    logger.info("  请手动访问以下链接，对比标题和时间：")
    logger.info("  https://wallstreetcn.com/news/global")
    logger.info("  http://localhost:1200/wallstreetcn/news/global")

    logger.info("\n" + "=" * 80)
    logger.info("✓ 验证完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
