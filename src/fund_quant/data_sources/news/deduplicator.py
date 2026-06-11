"""
新闻去重工具
"""
import pandas as pd

from fund_quant.common.logger import logger


class NewsDeduplicator:
    """新闻去重工具"""

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """
        新闻去重

        策略：
        1. 按 news_id 去重（同一来源内去重）
        2. 按 title + publish_time 去重（跨来源去重）

        Args:
            df: 新闻DataFrame

        Returns:
            去重后的DataFrame
        """
        if df is None or len(df) == 0:
            return df

        original_count = len(df)

        # 1. 按 news_id 去重
        df = df.drop_duplicates(subset=['news_id'], keep='first')
        logger.info(f"  按news_id去重: {original_count} → {len(df)}")

        # 2. 跨源去重（标题+时间）
        df['_dedup_key'] = (
            df['title'].str.strip() +
            df['publish_time'].astype(str)
        )
        before_count = len(df)
        df = df.drop_duplicates(subset=['_dedup_key'], keep='first')
        df = df.drop(columns=['_dedup_key'])

        if before_count > len(df):
            logger.info(f"  跨源去重: {before_count} → {len(df)}")

        return df


__all__ = ['NewsDeduplicator']
