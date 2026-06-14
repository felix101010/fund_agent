"""
Google News RSS 探测器
通过公开Google News RSS获取新闻标题和摘要（无需API key）

法律说明：
- 仅使用公开的Google News RSS服务
- 仅获取标题和摘要，不抓取付费正文
- 仅用于个人技术验证，不用于商业生产
- 如需正式使用Reuters，请使用Reuters/LSEG官方授权API
"""
import requests
import feedparser
from datetime import datetime
from typing import List
from urllib.parse import quote_plus
import time

from fund_quant.data_sources.global_news.free_news_probe_models import (
    FreeNewsSampleItem,
    FreeReutersProbeResult
)


class GoogleNewsRSSProbe:
    """
    Google News RSS 探测器

    功能：
    - 搜索指定query的新闻
    - 返回标题、摘要、发布时间、URL、source
    - 判断是否来自Reuters
    """

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, timeout: int = 10):
        """
        初始化

        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def probe(self, query: str, max_samples: int = 10) -> FreeReutersProbeResult:
        """
        探测查询结果

        Args:
            query: 查询词（例如 "Reuters NVIDIA"）
            max_samples: 最大样本数

        Returns:
            FreeReutersProbeResult
        """
        result = FreeReutersProbeResult(
            probe_name="google_news_rss",
            query=query,
            is_available=False,
            sample_count=0,
            has_title=False,
            has_summary=False,
            has_publish_time=False,
            has_url=False,
            has_body=False
        )

        try:
            # 构建RSS URL
            encoded_query = quote_plus(query)
            rss_url = f"{self.BASE_URL}?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            # 请求RSS
            response = requests.get(rss_url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            # 解析RSS
            feed = feedparser.parse(response.content)

            if not feed.entries:
                result.error_message = "No entries found"
                result.recommendation = "not_available"
                return result

            # 处理样本
            for entry in feed.entries[:max_samples]:
                # 提取字段
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                link = entry.get('link', '')
                published = entry.get('published_parsed', None)

                # 解析发布时间
                publish_time = None
                if published:
                    try:
                        publish_time = datetime(*published[:6])
                    except:
                        pass

                # 提取source
                source = entry.get('source', {}).get('title', 'Unknown')

                # 判断detected_source
                detected_source = self._detect_source(title, link, source)

                # 创建样本
                sample = FreeNewsSampleItem(
                    query=query,
                    title=title,
                    summary=summary,
                    publish_time=publish_time,
                    url=link,
                    source=source,
                    detected_source=detected_source,
                    language="en",
                    has_body=False,  # RSS不提供正文
                    raw={'entry': entry}
                )

                result.sample_items.append(sample)

            # 更新统计
            result.sample_count = len(result.sample_items)
            result.is_available = result.sample_count > 0

            if result.sample_items:
                result.has_title = all(item.title for item in result.sample_items)
                result.has_summary = any(item.summary for item in result.sample_items)
                result.has_publish_time = any(item.publish_time for item in result.sample_items)
                result.has_url = all(item.url for item in result.sample_items)

            # 推荐结论
            reuters_count = result.get_reuters_count()
            if reuters_count > 0:
                result.recommendation = "useful_for_title_level_test"
            elif result.sample_count > 0:
                result.recommendation = "test_only"
            else:
                result.recommendation = "not_available"

        except requests.RequestException as e:
            result.error_message = f"Request failed: {str(e)}"
            result.recommendation = "not_available"
        except Exception as e:
            result.error_message = f"Parse failed: {str(e)}"
            result.recommendation = "not_available"

        return result

    def _detect_source(self, title: str, link: str, source: str) -> str:
        """
        判断新闻来源

        Args:
            title: 标题
            link: 链接
            source: 原始source

        Returns:
            detected_source
        """
        # 统一小写
        title_lower = title.lower()
        link_lower = link.lower()
        source_lower = source.lower()

        # 判断Reuters
        if 'reuters' in source_lower:
            return 'Reuters'
        if 'reuters' in title_lower:
            return 'Reuters'
        if 'reuters.com' in link_lower:
            return 'Reuters'

        # 其他常见源
        if 'bloomberg' in source_lower or 'bloomberg' in link_lower:
            return 'Bloomberg'
        if 'cnbc' in source_lower or 'cnbc' in link_lower:
            return 'CNBC'
        if 'wsj' in source_lower or 'wsj' in link_lower or 'wall street journal' in source_lower:
            return 'Wall Street Journal'
        if 'ft.com' in link_lower or 'financial times' in source_lower:
            return 'Financial Times'

        # 返回原始source
        return source


__all__ = ['GoogleNewsRSSProbe']
