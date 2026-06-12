"""
新闻规则过滤模块
"""
from fund_quant.nlp.news_filter.filter_models import NewsItem, FilterResult
from fund_quant.nlp.news_filter.rule_filter import SimpleRuleFilter

__all__ = [
    'NewsItem',
    'FilterResult',
    'SimpleRuleFilter'
]
