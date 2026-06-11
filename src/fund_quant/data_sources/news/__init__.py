"""
新闻采集模块
"""
from fund_quant.data_sources.news.models import RawNews
from fund_quant.data_sources.news.cls_api_collector import ClsApiCollector
from fund_quant.data_sources.news.deduplicator import NewsDeduplicator
from fund_quant.data_sources.news.news_service import NewsService


__all__ = [
    'RawNews',
    'ClsApiCollector',
    'NewsDeduplicator',
    'NewsService',
]
