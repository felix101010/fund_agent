"""
华尔街见闻新闻采集器（RSS版本）
用于抓取宏观、海外市场、美股、商品等市场上下文新闻
"""
import feedparser
import hashlib
import re
from typing import List, Optional
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from fund_quant.common.logger import logger
from fund_quant.data_sources.news.models import RawNews


class WallstreetcnCollector:
    """华尔街见闻新闻采集器（RSS）"""

    SOURCE = "wallstreetcn"
    SOURCE_ROLE = "market_context"

    def __init__(self, rss_url: Optional[str] = None):
        """
        初始化采集器

        Args:
            rss_url: RSS地址，默认使用 RSSHub 全球高优先级版块
        """
        self.rss_url = rss_url or "http://127.0.0.1:1201/wallstreetcn/live/global/1"
        logger.info(f"华尔街见闻RSS采集器初始化成功: {self.rss_url}")

    def fetch_latest(self, limit: int = 30) -> List[RawNews]:
        """
        抓取最新新闻

        Args:
            limit: 抓取数量限制

        Returns:
            RawNews列表
        """
        try:
            logger.info(f"开始采集华尔街见闻RSS: {self.rss_url}")

            # 解析RSS
            feed = feedparser.parse(self.rss_url)

            if feed.bozo:
                # RSS解析出错
                error_msg = str(feed.bozo_exception)

                # 判断错误类型
                if 'text/html' in error_msg or 'HTML' in error_msg:
                    logger.error(f"RSS解析失败: {feed.bozo_exception}")
                    logger.error("RSSHub 已响应，但当前 URL 返回 HTML，不是 RSS XML")
                    logger.error("请检查 RSSHub 路由是否正确")
                    logger.error(f"当前推荐路由: http://127.0.0.1:1201/wallstreetcn/live/global/1")
                else:
                    logger.error(f"RSS解析失败: {feed.bozo_exception}")
                    logger.error("请确认 RSSHub 正在运行，默认地址: http://127.0.0.1:1201")
                return []

            entries = feed.entries[:limit]
            logger.info(f"  获取到 {len(entries)} 条RSS条目")

            if not entries:
                logger.warning("RSS返回空内容，请检查RSSHub服务")
                return []

            # 转换为 RawNews
            news_list = []
            now = datetime.now(timezone.utc)

            for entry in entries:
                try:
                    news_item = self._parse_entry(entry, now)
                    if news_item:
                        news_list.append(news_item)
                except Exception as e:
                    # 打印标题方便定位
                    title = entry.get('title', 'Unknown')
                    logger.warning(f"  解析条目失败: title={title}, error={e}")
                    continue

            if len(news_list) == 0 and len(entries) > 0:
                logger.error("RSSHub 已正常返回数据，但条目解析失败，请检查时间解析、字段映射或 RawNewsItem 构造逻辑")

            logger.info(f"✓ 华尔街见闻RSS采集完成: {len(news_list)} 条")
            return news_list

        except Exception as e:
            logger.error(f"华尔街见闻采集失败: {e}")
            logger.error("请确认 RSSHub 正在运行，默认地址: http://127.0.0.1:1201")
            return []

    def _parse_entry(self, entry: dict, now: datetime) -> Optional[RawNews]:
        """
        解析单个RSS条目

        Args:
            entry: feedparser entry对象
            now: 当前时间

        Returns:
            RawNews对象或None
        """
        # 提取标题
        title = entry.get('title', '').strip()
        if not title:
            return None

        # 提取链接
        link = entry.get('link', '')

        # 提取内容
        content = ''
        if 'summary' in entry:
            content = entry['summary']
        elif 'content' in entry and entry['content']:
            content = entry['content'][0].get('value', '')
        elif 'description' in entry:
            content = entry['description']

        # 清洗文本
        title = self._clean_text(title)
        content = self._clean_text(content)

        # 提取发布时间
        publish_time = self._parse_time(entry)

        # 生成稳定的 news_id
        news_id = self._generate_news_id(link, title, publish_time)

        # 计算延迟
        delay_seconds = int((now - publish_time).total_seconds())

        return RawNews(
            news_id=news_id,
            source=self.SOURCE,
            title=title,
            content=content,
            publish_time=publish_time,
            url=link,
            source_role=self.SOURCE_ROLE,
            raw_json=str(entry),
            first_seen_time=now,
            delay_seconds=delay_seconds,
            created_at=now,
        )

    def _clean_text(self, text: str) -> str:
        """
        清洗文本

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ''

        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 去除多余空白字符
        text = re.sub(r'\s+', ' ', text)

        # 去除首尾空白
        text = text.strip()

        return text

    def _parse_time(self, entry: dict) -> datetime:
        """
        解析发布时间（确保返回 timezone-aware datetime）

        Args:
            entry: RSS条目

        Returns:
            发布时间（UTC时区）
        """
        # 优先使用字符串格式的时间字段
        for attr in ('published', 'updated'):
            value = getattr(entry, attr, None)
            if value:
                try:
                    dt = parsedate_to_datetime(value)
                    return self._ensure_aware(dt)
                except Exception:
                    pass

        # 其次使用 time.struct_time 格式
        for attr in ('published_parsed', 'updated_parsed'):
            value = getattr(entry, attr, None)
            if value:
                try:
                    # struct_time 前6个元素：年月日时分秒
                    dt = datetime(*value[:6], tzinfo=timezone.utc)
                    return dt
                except Exception:
                    pass

        # 如果都失败，使用当前UTC时间
        return datetime.now(timezone.utc)

    def _ensure_aware(self, dt: datetime) -> datetime:
        """
        确保 datetime 是 timezone-aware，如果是 naive 则补充 UTC 时区

        Args:
            dt: datetime 对象

        Returns:
            timezone-aware datetime（UTC时区）
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _generate_news_id(self, link: str, title: str, publish_time: datetime) -> str:
        """
        生成稳定的 news_id

        优先使用链接生成，fallback到标题+时间

        Args:
            link: 新闻链接
            title: 标题
            publish_time: 发布时间

        Returns:
            news_id，格式：wscn_xxxxxxxxxxxxxxxx
        """
        if link:
            # 从链接中提取ID
            # 例如：https://wallstreetcn.com/articles/3712345
            match = re.search(r'/articles/(\d+)', link)
            if match:
                article_id = match.group(1)
                return f"wscn_{article_id}"

            # 如果链接没有明确ID，使用链接hash
            link_hash = hashlib.md5(link.encode()).hexdigest()[:16]
            return f"wscn_{link_hash}"

        # fallback: 使用标题+时间生成hash
        content = f"{title}_{publish_time.strftime('%Y%m%d%H%M%S')}"
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"wscn_{content_hash}"


__all__ = ['WallstreetcnCollector']
