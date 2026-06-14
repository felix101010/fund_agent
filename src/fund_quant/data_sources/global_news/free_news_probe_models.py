"""
免费新闻源探测数据模型
仅用于技术验证，不用于商业生产
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class FreeNewsSampleItem:
    """免费新闻样本项（标题级）"""
    query: str  # 查询词
    title: str  # 标题
    summary: str  # 摘要
    publish_time: Optional[datetime]  # 发布时间
    url: str  # URL
    source: str  # 聚合源返回的原始source
    detected_source: str  # 通过标题/链接判断的source
    language: str = "en"  # 语言
    has_body: bool = False  # 是否有正文（免费聚合源通常为False）
    topics: List[str] = field(default_factory=list)  # 主题标签
    tickers: List[str] = field(default_factory=list)  # 股票代码
    raw: dict = field(default_factory=dict)  # 原始数据


@dataclass
class FreeReutersProbeResult:
    """免费Reuters探测结果"""
    probe_name: str  # 探测器名称 (google_news_rss / yahoo_finance)
    query: str  # 查询词
    is_available: bool  # 是否可用
    sample_count: int  # 样本数
    has_title: bool  # 是否有标题
    has_summary: bool  # 是否有摘要
    has_publish_time: bool  # 是否有发布时间
    has_url: bool  # 是否有URL
    has_body: bool  # 是否有正文
    error_message: str = ""  # 错误信息
    recommendation: str = "test_only"  # test_only / not_available / unstable / useful_for_title_level_test
    legal_note: str = "仅用于公开聚合源标题/摘要级测试，不用于商业生产"
    sample_items: List[FreeNewsSampleItem] = field(default_factory=list)  # 样本列表

    def get_reuters_count(self) -> int:
        """统计detected_source=Reuters的样本数"""
        return sum(1 for item in self.sample_items if 'reuters' in item.detected_source.lower())


__all__ = ['FreeNewsSampleItem', 'FreeReutersProbeResult']
