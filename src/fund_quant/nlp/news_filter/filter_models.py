"""
新闻过滤数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    """新闻条目"""
    news_id: str
    source: str
    title: str
    content: str
    publish_time: datetime | str

    def __post_init__(self):
        """确保 publish_time 是 datetime 类型"""
        if isinstance(self.publish_time, str):
            try:
                self.publish_time = datetime.fromisoformat(self.publish_time)
            except ValueError:
                # 如果解析失败，保持字符串
                pass


@dataclass
class FilterResult:
    """过滤结果"""
    news_id: str
    action: str  # archive, low_value, candidate, analyze, risk, unknown
    need_ai: bool
    pre_score: int
    matched_keywords: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)

    def __post_init__(self):
        """验证 action 值"""
        valid_actions = {'archive', 'low_value', 'candidate', 'analyze', 'risk', 'unknown'}
        if self.action not in valid_actions:
            raise ValueError(f"Invalid action: {self.action}. Must be one of {valid_actions}")


__all__ = ['NewsItem', 'FilterResult']
