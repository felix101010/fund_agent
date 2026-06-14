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
    """AI 事件抽取结果（增强版）"""
    news_id: str
    is_market_relevant: bool
    event_type: str
    theme: str  # AI原始主题，逗号分隔
    sub_themes: list[str]
    related_stocks: list[RelatedStock]
    sentiment: str
    event_level: str
    novelty_type: str
    summary: str
    confidence: float

    # 风险标记
    risk_flags: list[str] = field(default_factory=list)

    # 验证和后处理
    raw_ai_response: str = ""
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)
    related_entities: list = field(default_factory=list)  # 非股票实体
    postprocess_notes: list[str] = field(default_factory=list)  # 后处理修正记录

    # 主题标准化字段（新增）
    raw_themes: str = ""  # AI原始主题，保留调试用
    primary_theme_id: str = ""  # 标准主题ID
    primary_theme_name: str = ""  # 标准主题中文名
    normalized_themes: list = field(default_factory=list)  # 标准化主题列表
    theme_confidence: float = 0.0  # 主题映射置信度
    mapping_notes: list[str] = field(default_factory=list)  # 主题/市场映射说明

    # 市场映射字段（新增）
    related_indices: list[str] = field(default_factory=list)  # 相关指数
    related_etfs: list[str] = field(default_factory=list)  # 相关ETF
    candidate_stock_pool_theme: str = ""  # 候选股票池主题

    # 评分字段（新增）
    final_score: float = 0.0  # 事件最终分数
    trade_priority: str = "watch"  # urgent/high/candidate/watch

    @property
    def themes(self) -> list[str]:
        """获取主题列表（从 theme 字段解析）"""
        if not self.theme:
            return []
        return [t.strip() for t in self.theme.split(",") if t.strip()]


__all__ = ['RelatedStock', 'AIEventResult']
