#!/usr/bin/env python3
"""
查看财联社采集数据并分析实时性
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.common.logger import logger


def main():
    """查看财联社数据"""
    client = ClickHouseClient()

    logger.info("=" * 80)
    logger.info("财联社新闻数据查看与实时性分析")
    logger.info("=" * 80)

    # 1. 查看最新10条新闻
    logger.info("\n【1. 最新10条新闻】")
    sql = """
    SELECT
        news_id,
        title,
        publish_time,
        first_seen_time,
        delay_seconds,
        length(content) as content_length,
        url
    FROM raw_news
    WHERE source = 'cls'
    ORDER BY publish_time DESC
    LIMIT 10
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        for idx, row in df.iterrows():
            logger.info(f"\n{idx + 1}. {row['title'][:80]}")
            logger.info(f"   发布时间: {row['publish_time']}")
            logger.info(f"   采集时间: {row['first_seen_time']}")
            logger.info(f"   采集延迟: {row['delay_seconds']}秒 ({row['delay_seconds'] // 60}分钟)")
            logger.info(f"   内容长度: {row['content_length']}字")
            logger.info(f"   链接: {row['url']}")
    else:
        logger.warning("  没有财联社数据")
        return

    # 2. 数据总量统计
    logger.info("\n【2. 数据总量统计】")
    sql = """
    SELECT
        count() as total,
        min(publish_time) as earliest,
        max(publish_time) as latest,
        dateDiff('hour', min(publish_time), max(publish_time)) as time_span_hours
    FROM raw_news
    WHERE source = 'cls'
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        row = df.iloc[0]
        logger.info(f"  总数: {row['total']} 条")
        logger.info(f"  最早: {row['earliest']}")
        logger.info(f"  最新: {row['latest']}")
        logger.info(f"  时间跨度: {row['time_span_hours']} 小时")

    # 3. 实时性分析（核心）
    logger.info("\n【3. 实时性分析】")
    sql = """
    SELECT
        count() as total,
        min(delay_seconds) as min_delay,
        max(delay_seconds) as max_delay,
        avg(delay_seconds) as avg_delay,
        quantile(0.5)(delay_seconds) as median_delay,
        quantile(0.9)(delay_seconds) as p90_delay,
        quantile(0.95)(delay_seconds) as p95_delay
    FROM raw_news
    WHERE source = 'cls'
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        row = df.iloc[0]
        logger.info(f"  总数: {row['total']}")
        logger.info(f"  最小延迟: {row['min_delay']}秒 ({row['min_delay'] // 60}分钟)")
        logger.info(f"  最大延迟: {row['max_delay']}秒 ({row['max_delay'] // 60}分钟)")
        logger.info(f"  平均延迟: {row['avg_delay']:.0f}秒 ({row['avg_delay'] // 60:.0f}分钟)")
        logger.info(f"  中位延迟: {row['median_delay']:.0f}秒 ({row['median_delay'] // 60:.0f}分钟)")
        logger.info(f"  P90延迟: {row['p90_delay']:.0f}秒 ({row['p90_delay'] // 60:.0f}分钟)")
        logger.info(f"  P95延迟: {row['p95_delay']:.0f}秒 ({row['p95_delay'] // 60:.0f}分钟)")

        # 实时性评估
        logger.info("\n  实时性评估:")
        avg_minutes = row['avg_delay'] / 60
        if avg_minutes < 2:
            logger.info(f"  ✓ 优秀 - 平均延迟 {avg_minutes:.1f} 分钟，达到实时标准")
        elif avg_minutes < 5:
            logger.info(f"  ✓ 良好 - 平均延迟 {avg_minutes:.1f} 分钟，接近实时")
        elif avg_minutes < 30:
            logger.info(f"  ⚠ 一般 - 平均延迟 {avg_minutes:.1f} 分钟，有延迟")
        else:
            logger.info(f"  ✗ 较差 - 平均延迟 {avg_minutes:.1f} 分钟，延迟较大")

    # 4. 延迟分布
    logger.info("\n【4. 延迟分布】")
    sql = """
    SELECT
        CASE
            WHEN delay_seconds < 60 THEN '<1分钟'
            WHEN delay_seconds < 120 THEN '1-2分钟'
            WHEN delay_seconds < 300 THEN '2-5分钟'
            WHEN delay_seconds < 600 THEN '5-10分钟'
            WHEN delay_seconds < 1800 THEN '10-30分钟'
            WHEN delay_seconds < 3600 THEN '30-60分钟'
            ELSE '>1小时'
        END as delay_range,
        count() as cnt,
        round(count() * 100.0 / sum(count()) OVER (), 2) as percentage
    FROM raw_news
    WHERE source = 'cls'
    GROUP BY delay_range
    ORDER BY min(delay_seconds)
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        for _, row in df.iterrows():
            logger.info(f"  {row['delay_range']:12s}: {row['cnt']:4d} 条 ({row['percentage']:5.1f}%)")

    # 5. 按小时统计
    logger.info("\n【5. 按小时统计（最近24小时）】")
    sql = """
    SELECT
        toStartOfHour(publish_time) as hour,
        count() as cnt
    FROM raw_news
    WHERE source = 'cls'
        AND publish_time >= now() - INTERVAL 24 HOUR
    GROUP BY hour
    ORDER BY hour DESC
    LIMIT 24
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        for _, row in df.iterrows():
            logger.info(f"  {row['hour']}: {row['cnt']:3d} 条")
    else:
        logger.info("  最近24小时无数据")

    # 6. 内容完整性检查
    logger.info("\n【6. 内容完整性检查】")
    sql = """
    SELECT
        count() as total,
        countIf(title = '') as empty_title,
        countIf(content = '') as empty_content,
        countIf(url = '') as empty_url,
        countIf(length(content) < 20) as short_content,
        avg(length(content)) as avg_content_length
    FROM raw_news
    WHERE source = 'cls'
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        row = df.iloc[0]
        logger.info(f"  总数: {row['total']}")
        logger.info(f"  空标题: {row['empty_title']}")
        logger.info(f"  空内容: {row['empty_content']}")
        logger.info(f"  空链接: {row['empty_url']}")
        logger.info(f"  内容过短(<20字): {row['short_content']}")
        logger.info(f"  平均内容长度: {row['avg_content_length']:.0f} 字")

    # 7. 查看样本内容
    logger.info("\n【7. 最新一条新闻样本】")
    sql = """
    SELECT
        news_id,
        title,
        content,
        publish_time,
        first_seen_time,
        delay_seconds
    FROM raw_news
    WHERE source = 'cls'
    ORDER BY publish_time DESC
    LIMIT 1
    """

    df = client.query_df(sql)

    if df is not None and not df.empty:
        row = df.iloc[0]
        logger.info(f"\n新闻ID: {row['news_id']}")
        logger.info(f"标题: {row['title']}")
        logger.info(f"内容: {row['content'][:200]}{'...' if len(row['content']) > 200 else ''}")
        logger.info(f"发布时间: {row['publish_time']}")
        logger.info(f"采集时间: {row['first_seen_time']}")
        logger.info(f"采集延迟: {row['delay_seconds']}秒")

    logger.info("\n" + "=" * 80)
    logger.info("✓ 分析完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
