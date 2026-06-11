"""
财联社快讯采集器（API版本）
直接调用财联社API获取数据
"""
import requests
import time
import json
from typing import List, Optional
from datetime import datetime
import pandas as pd

from fund_quant.common.logger import logger


class ClsApiCollector:
    """财联社快讯采集器（API直接调用）"""

    # 财联社API（从Playwright拦截获得）
    API_URL = "https://www.cls.cn/api/cache"

    # 固定参数
    PARAMS = {
        'app': 'CailianpressWeb',
        'name': 'telegraph',
        'os': 'web',
        'sv': '8.7.9',
        'sign': '6c73b056a64891cdc257dcf1914464ad',  # 需要研究sign算法，目前使用固定值
    }

    def __init__(self):
        """初始化采集器"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.cls.cn/telegraph",
        })
        logger.info("财联社API采集器初始化成功")

    def fetch_latest(self, limit: int = 50) -> pd.DataFrame:
        """
        采集最新财联社快讯

        Args:
            limit: 采集数量

        Returns:
            DataFrame
        """
        logger.info(f"开始采集财联社快讯（API）: {self.API_URL}")

        try:
            response = self.session.get(self.API_URL, params=self.PARAMS, timeout=30)

            if response.status_code != 200:
                logger.error(f"API请求失败，状态码: {response.status_code}")
                return pd.DataFrame()

            data = response.json()

            if data.get('errno') != 0:
                logger.error(f"API返回错误: {data}")
                return pd.DataFrame()

            roll_data = data.get('data', {}).get('roll_data', [])

            if not roll_data:
                logger.warning("API返回数据为空")
                return pd.DataFrame()

            logger.info(f"  获取到 {len(roll_data)} 条数据")

            # 转换为标准格式
            news_list = []
            now = datetime.now()

            for item in roll_data[:limit]:
                try:
                    news_item = self._parse_item(item, now)
                    if news_item:
                        news_list.append(news_item)
                except Exception as e:
                    logger.warning(f"  解析数据失败: {e}")
                    continue

            if not news_list:
                logger.warning("未解析出有效新闻")
                return pd.DataFrame()

            df = pd.DataFrame(news_list)
            logger.info(f"✓ 财联社API采集完成: {len(df)} 条")

            return df

        except Exception as e:
            logger.error(f"采集失败: {e}")
            return pd.DataFrame()

    def _parse_item(self, item: dict, now: datetime) -> Optional[dict]:
        """解析单条新闻"""
        news_id = item.get('id')
        if not news_id:
            return None

        # 解析时间（Unix时间戳）
        ctime = item.get('ctime')
        if ctime:
            publish_time = datetime.fromtimestamp(ctime)
        else:
            publish_time = now

        # 计算延迟
        delay_seconds = int((now - publish_time).total_seconds())

        return {
            'news_id': f"cls_{news_id}",
            'source': 'cls',
            'title': item.get('title', ''),
            'content': item.get('content', '') or item.get('brief', ''),
            'publish_time': publish_time,
            'url': f"https://www.cls.cn/detail/{news_id}",
            'raw_json': json.dumps(item, ensure_ascii=False),
            'first_seen_time': now,
            'delay_seconds': delay_seconds,
            'created_at': now,
        }


__all__ = ['ClsApiCollector']
