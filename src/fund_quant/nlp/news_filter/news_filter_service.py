"""
新闻过滤服务
"""
from typing import List

from fund_quant.nlp.news_filter.filter_models import NewsItem, FilterResult
from fund_quant.nlp.news_filter.rule_filter import SimpleRuleFilter


class NewsFilterService:
    """新闻过滤服务"""

    def __init__(self):
        """初始化服务"""
        self.filter = SimpleRuleFilter()

    def filter_news_batch(self, news_list: List[NewsItem]) -> List[FilterResult]:
        """
        批量过滤新闻

        Args:
            news_list: 新闻列表

        Returns:
            过滤结果列表
        """
        results = []
        for news in news_list:
            result = self.filter.filter(news)
            results.append(result)
        return results

    def filter_and_group(self, news_list: List[NewsItem]) -> dict[str, List[FilterResult]]:
        """
        批量过滤并按 action 分组

        Args:
            news_list: 新闻列表

        Returns:
            按 action 分组的结果字典
        """
        results = self.filter_news_batch(news_list)

        grouped = {
            'risk': [],
            'analyze': [],
            'candidate': [],
            'low_value': [],
            'archive': [],
            'unknown': []
        }

        for result in results:
            if result.action in grouped:
                grouped[result.action].append(result)

        return grouped

    def get_ai_candidates(self, news_list: List[NewsItem]) -> List[FilterResult]:
        """
        获取需要进入 AI 分析的新闻

        Args:
            news_list: 新闻列表

        Returns:
            need_ai=True 的过滤结果列表
        """
        results = self.filter_news_batch(news_list)
        return [r for r in results if r.need_ai]


__all__ = ['NewsFilterService']
