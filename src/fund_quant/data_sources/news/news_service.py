"""
新闻采集服务（业务编排层）
"""
from typing import Optional, List
import pandas as pd

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.data_sources.news.cls_api_collector import ClsApiCollector
from fund_quant.data_sources.news.wallstreetcn_collector import WallstreetcnCollector
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
        self.cls_collector = ClsApiCollector()
        self.wscn_collector = WallstreetcnCollector()
        self.client = ClickHouseClient()
        self.limit = limit

    def fetch_latest(self, source: str, limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        按来源抓取新闻

        Args:
            source: 新闻源 (cls/wallstreetcn)
            limit: 抓取数量，None则使用默认

        Returns:
            新闻DataFrame，失败返回None
        """
        limit = limit or self.limit

        if source == "cls":
            return self.cls_collector.fetch_latest(limit=limit)
        elif source == "wallstreetcn":
            news_list = self.wscn_collector.fetch_latest(limit=limit)
            if not news_list:
                return None
            # 转换为DataFrame
            return pd.DataFrame([n.to_dict() for n in news_list])
        else:
            logger.error(f"不支持的新闻源: {source}")
            return None

    def fetch_all_latest(self, limit_per_source: int = 20) -> pd.DataFrame:
        """
        抓取所有来源的最新新闻

        Args:
            limit_per_source: 每个来源的抓取数量

        Returns:
            合并后的DataFrame
        """
        all_news = []

        # 抓取财联社
        try:
            cls_df = self.fetch_latest("cls", limit=limit_per_source)
            if cls_df is not None and not cls_df.empty:
                all_news.append(cls_df)
                logger.info(f"✓ 财联社: {len(cls_df)} 条")
        except Exception as e:
            logger.error(f"✗ 财联社采集失败: {e}")

        # 抓取华尔街见闻
        try:
            wscn_df = self.fetch_latest("wallstreetcn", limit=limit_per_source)
            if wscn_df is not None and not wscn_df.empty:
                all_news.append(wscn_df)
                logger.info(f"✓ 华尔街见闻: {len(wscn_df)} 条")
        except Exception as e:
            logger.error(f"✗ 华尔街见闻采集失败: {e}")

        # 合并
        if not all_news:
            logger.warning("所有新闻源采集均失败")
            return pd.DataFrame()

        combined_df = pd.concat(all_news, ignore_index=True)
        logger.info(f"✓ 合并后总计: {len(combined_df)} 条")

        return combined_df

    def fetch_and_store(self) -> Optional[pd.DataFrame]:
        """
        采集财联社新闻并存入数据库（保持向后兼容）

        Returns:
            采集到的DataFrame，失败返回None
        """
        logger.info("=" * 80)
        logger.info("开始采集财联社新闻")
        logger.info("=" * 80)

        # 1. 抓取
        df = self.cls_collector.fetch_latest(limit=self.limit)
        if df is None or len(df) == 0:
            logger.warning("采集失败或无新数据")
            return None

        # 2. 去重
        df = NewsDeduplicator.remove_duplicates(df)

        # 3. 存储
        inserted = self.client.insert_df('raw_news', df)
        logger.info(f"\n✓ 已存储 {inserted} 条")

        # 4. 统计
        total_sql = "SELECT COUNT(*) as total FROM raw_news WHERE source = 'cls'"
        total_result = self.client.query_df(total_sql)
        if total_result is not None and not total_result.empty:
            total = total_result.iloc[0]['total']
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
