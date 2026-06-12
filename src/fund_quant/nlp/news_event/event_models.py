"""
新闻事件数据模型（用于后续入库）
"""
from dataclasses import dataclass


@dataclass
class NewsEvent:
    """新闻事件（轻量级，用于入库）"""
    event_id: str
    news_id: str
    event_type: str
    theme: str
    sentiment: str
    event_level: str
    novelty_type: str
    summary: str
    confidence: float


__all__ = ['NewsEvent']
