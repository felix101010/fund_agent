"""
新闻数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawNews:
    """
    原始新闻数据模型（对应 ClickHouse raw_news 表）

    职责：只存储原始采集数据，不做任何分析
    """

    # 必填字段
    news_id: str                    # 新闻唯一ID（格式：source_原始id）
    source: str                     # 来源：cls/eastmoney/cninfo
    publish_time: datetime          # 发布时间
    title: str                      # 标题
    content: str                    # 正文

    # 可选字段
    url: Optional[str] = None       # 新闻链接
    raw_json: Optional[str] = None  # 原始JSON（用于溯源）

    # 时间追踪
    first_seen_time: Optional[datetime] = None  # 系统首次发现时间
    delay_seconds: Optional[int] = None         # 发现延迟（秒）

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        """转换为字典（用于写入数据库）"""
        return {
            'news_id': self.news_id,
            'source': self.source,
            'publish_time': self.publish_time,
            'title': self.title,
            'content': self.content,
            'url': self.url,
            'raw_json': self.raw_json,
            'first_seen_time': self.first_seen_time,
            'delay_seconds': self.delay_seconds,
            'created_at': self.created_at,
        }


__all__ = ['RawNews']
