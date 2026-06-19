"""
Company IR (投资者关系) 新闻源模块
支持美股公司IR网站新闻采集
"""
from .ir_company_config import (
    IR_COMPANIES,
    get_ir_company_config,
    list_enabled_ir_tickers,
    list_ir_tickers_by_tier,
    list_all_ir_tickers
)
from .ir_rss_collector import IRRSSCollector
from .ir_page_collector import IRPageCollector
from .ir_page_list_collector import IRPageListCollector
from .ir_document_downloader import IRDocumentDownloader
from .ir_normalizer import normalize_ir_item
from .ir_rules import IRRules
from .ir_deduplicator import deduplicate_ir_items

__all__ = [
    'IR_COMPANIES',
    'get_ir_company_config',
    'list_enabled_ir_tickers',
    'list_ir_tickers_by_tier',
    'list_all_ir_tickers',
    'IRRSSCollector',
    'IRPageCollector',
    'IRPageListCollector',
    'IRDocumentDownloader',
    'normalize_ir_item',
    'IRRules',
    'deduplicate_ir_items'
]
