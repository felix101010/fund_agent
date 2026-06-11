"""
新闻采集服务（业务编排层）
"""
from typing import Optional
import pandas as pd

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.data_sources.news.cls_api_collector import ClsApiCollector
from fund_quant.data_sources.news.deduplicator import NewsDeduplicator
from fund_quant.common.logger import logger


class NewsService:
    """新闻采集服务"""

    def __init__(self, limit: int = 50):
        """
        初始化服务

        Args:
            limit: 采集数量
        """
        self.collector = ClsApiCollector()
        self.client = ClickHouseClient()
        self.limit = limit

    def fetch_and_store(self) -> Optional[pd.DataFrame]:
        """
        采集财联社新闻并存入数据库

        Returns:
            采集到的DataFrame，失败返回None
        """
        logger.info("=" * 80)
        logger.info("开始采集财联社新闻")
        logger.info("=" * 80)

        # 1. 采集数据
        df = self.collector.fetch_latest(limit=self.limit)

        if df.empty:
            logger.error("采集失败，无数据")
            return None

        logger.info(f"\n采集到 {len(df)} 条数据")

        # 2. 去重
        df = NewsDeduplicator.remove_duplicates(df)
        logger.info(f"去重后 {len(df)} 条数据")

        # 3. 写入数据库
        records = df.to_dict('records')

        try:
            self.client.insert_many('raw_news', records)
            logger.info(f"✓ 成功写入 {len(records)} 条数据到数据库")
        except Exception as e:
            logger.error(f"✗ 写入数据库失败: {e}")
            return None

        # 4. 验证写入
        sql = "SELECT count() as cnt FROM raw_news WHERE source = 'cls'"
        result = self.client.query_df(sql)

        if result is not None and not result.empty:
            total = result.iloc[0]['cnt']
            logger.info(f"\n数据库中共有 {total} 条财联社新闻")

        # 5. 显示最新3条
        self._show_latest(3)

        logger.info("\n" + "=" * 80)
        logger.info("✓ 采集完成")
        logger.info("=" * 80)

        return df

    def _show_latest(self, n: int = 3):
        """显示最新N条新闻"""
        logger.info(f"\n最新{n}条新闻：")
        sql = f"""
        SELECT title, publish_time, delay_seconds
        FROM raw_news
        WHERE source = 'cls'
        ORDER BY publish_time DESC
        LIMIT {n}
        """
        result = self.client.query_df(sql)

        if result is not None and not result.empty:
            for idx, row in result.iterrows():
                logger.info(f"\n{idx + 1}. {row['title'][:60]}")
                logger.info(f"   发布时间: {row['publish_time']}")
                logger.info(f"   采集延迟: {row['delay_seconds']}秒")


__all__ = ['NewsService']
