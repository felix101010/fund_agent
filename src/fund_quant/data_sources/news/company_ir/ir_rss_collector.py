"""
Company IR RSS采集器（增强版）
支持RSS feed自动发现
"""
import logging
from datetime import datetime, timedelta
from typing import List

try:
    import feedparser
    import requests
except ImportError:
    feedparser = None
    requests = None

from .ir_company_config import get_ir_company_config
from .ir_rss_utils import is_probable_feed_response, discover_feed_urls

logger = logging.getLogger(__name__)


class IRRSSCollector:
    """
    IR RSS采集器（增强版）

    职责：
    - 抓取真实RSS feed
    - 自动发现RSS feed链接
    - 返回原始item列表
    """

    def __init__(self):
        """初始化"""
        if feedparser is None:
            logger.warning("feedparser未安装，RSS采集功能不可用")
        if requests is None:
            logger.warning("requests未安装，RSS采集功能不可用")

    def collect(self, ticker: str, days: int = 30) -> List[dict]:
        """
        采集指定公司的IR新闻

        Args:
            ticker: 股票代码
            days: 采集最近N天的新闻

        Returns:
            原始item列表
        """
        if feedparser is None or requests is None:
            logger.warning(f"依赖库未安装，跳过{ticker}")
            return []

        # 获取公司配置
        config = get_ir_company_config(ticker)
        if not config:
            logger.warning(f"未找到{ticker}的配置")
            return []

        # 收集所有feed URLs
        feed_urls = []

        # 1. 添加配置中的真实RSS URLs
        rss_urls = config.get('rss_urls', [])
        feed_urls.extend(rss_urls)
        logger.info(f"{ticker}: 配置了{len(rss_urls)}个RSS URL")

        # 2. 从discovery URLs中发现feed
        discovery_urls = config.get('rss_discovery_urls', [])
        for discovery_url in discovery_urls:
            try:
                discovered = self._discover_feeds(discovery_url)
                if discovered:
                    logger.info(f"从{discovery_url}发现{len(discovered)}个feed")
                    feed_urls.extend(discovered)
            except Exception as e:
                logger.warning(f"发现feed失败: {discovery_url}, {e}")

        # 3. 去重
        feed_urls = list(dict.fromkeys(feed_urls))
        logger.info(f"{ticker}: 总共{len(feed_urls)}个feed URL待处理")

        # 4. 逐个抓取feed
        items = []
        for feed_url in feed_urls:
            try:
                feed_items = self._fetch_feed(feed_url, days)
                if feed_items:
                    logger.info(f"从{feed_url}采集到{len(feed_items)}条")
                    items.extend(feed_items)
            except Exception as e:
                logger.warning(f"采集feed失败: {feed_url}, {e}")

        return items

    def _discover_feeds(self, url: str) -> List[str]:
        """
        从URL发现RSS feed链接

        Args:
            url: 发现页URL

        Returns:
            发现的feed URL列表
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()

            # 检查是否已经是feed
            if is_probable_feed_response(
                response.headers.get('Content-Type', ''),
                response.text
            ):
                logger.info(f"{url}本身就是feed")
                return [url]

            # 从HTML中发现feed
            discovered = discover_feed_urls(response.text, url)
            return discovered

        except Exception as e:
            logger.warning(f"发现失败: {url}, {e}")
            return []

    def _fetch_feed(self, feed_url: str, days: int) -> List[dict]:
        """
        抓取单个RSS feed

        Args:
            feed_url: Feed URL
            days: 天数过滤

        Returns:
            item列表
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            # 请求feed
            response = requests.get(feed_url, headers=headers, timeout=20)
            response.raise_for_status()

            # 验证是否是feed
            if not is_probable_feed_response(
                response.headers.get('Content-Type', ''),
                response.text
            ):
                logger.warning(f"跳过非feed URL: {feed_url}")
                return []

            # 解析feed
            feed = feedparser.parse(response.content)

            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed解析警告: {feed_url}, {feed.bozo_exception}")

            if not feed.entries:
                logger.warning(f"Feed无条目: {feed_url}")
                return []

            # 提取entries
            items = []
            cutoff_date = datetime.now() - timedelta(days=days)

            for entry in feed.entries:
                try:
                    item = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', '') or entry.get('updated', ''),
                        'summary': entry.get('summary', '') or entry.get('description', ''),
                        'source_detail': 'ir_rss'
                    }

                    # 日期过滤
                    if item['published']:
                        try:
                            from email.utils import parsedate_to_datetime
                            pub_dt = parsedate_to_datetime(item['published'])
                            if pub_dt < cutoff_date:
                                continue
                        except:
                            pass

                    items.append(item)

                except Exception as e:
                    logger.warning(f"解析entry失败: {e}")
                    continue

            return items

        except Exception as e:
            logger.error(f"抓取feed失败: {feed_url}, {e}")
            return []


__all__ = ['IRRSSCollector']
