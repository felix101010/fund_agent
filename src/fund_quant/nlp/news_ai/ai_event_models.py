"""
AI 事件抽取数据模型
"""
from dataclasses import dataclass, field


@dataclass
class RelatedStock:
    """关联股票"""
    code: str
    name: str
    reason: str


@dataclass
class AIEventResult:
    """AI 事件抽取结果"""
    news_id: str
    is_market_relevant: bool
    event_type: str
    theme: str  # 向后兼容，存储逗号分隔的主题字符串
    sub_themes: list[str]
    related_stocks: list[RelatedStock]
    sentiment: str
    event_level: str
    novelty_type: str
    summary: str
    confidence: float
    risk_flags: list[str] = field(default_factory=list)
    raw_ai_response: str = ""
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)

    @property
    def themes(self) -> list[str]:
        """获取主题列表（从 theme 字段解析）"""
        if not self.theme:
            return []
        return [t.strip() for t in self.theme.split(",") if t.strip()]


__all__ = ['RelatedStock', 'AIEventResult']
