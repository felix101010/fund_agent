"""
Company IR新闻标准化器
将原始RSS/页面数据标准化为统一格式
"""
import hashlib
from datetime import datetime
from typing import Optional


def normalize_ir_item(
    ticker: str,
    company_config: dict,
    raw_item: dict,
    article_detail: Optional[dict] = None
) -> dict:
    """
    标准化IR新闻item

    Args:
        ticker: 股票代码
        company_config: 公司配置
        raw_item: RSS或页面原始数据
        article_detail: 页面详情（可选）

    Returns:
        标准化的新闻item
    """
    # 提取基础字段
    title = raw_item.get('title', '') or ''
    link = raw_item.get('link', '') or ''
    summary = raw_item.get('summary', '') or ''
    published = raw_item.get('published', '')
    source_detail = raw_item.get('source_detail', 'ir_rss')

    # content优先使用article_detail
    if article_detail and article_detail.get('content'):
        content = article_detail['content']
    else:
        content = summary

    # 标准化publish_time
    publish_time = _normalize_publish_time(published)

    # 生成稳定news_id
    news_id = _generate_news_id('company_ir', ticker, link)

    # 提取attachments
    attachments = []
    if article_detail and article_detail.get('attachments'):
        attachments = article_detail['attachments']

    # 构建标准化item
    item = {
        'source': 'company_ir',
        'source_detail': source_detail,
        'news_id': news_id,
        'ticker': ticker.upper(),
        'company_name': company_config.get('company_name', ''),
        'title': title,
        'content': content,
        'summary': summary,
        'publish_time': publish_time,
        'url': link,
        'document_type': '',  # 由ir_rules.classify填充
        'event_hint': '',     # 由ir_rules.classify填充
        'pre_score': 0,       # 由ir_rules.classify填充
        'need_ai': True,      # 由ir_rules.classify填充
        'attachments': attachments,
        'raw': raw_item       # 保留原始数据
    }

    return item


def _normalize_publish_time(published: str) -> str:
    """
    标准化发布时间为ISO格式

    Args:
        published: 原始发布时间字符串

    Returns:
        ISO格式时间字符串
    """
    if not published:
        return datetime.now().isoformat()

    # 尝试解析常见格式
    try:
        # RFC 2822格式（RSS常用）
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published)
        return dt.isoformat()
    except:
        pass

    try:
        # ISO格式
        dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
        return dt.isoformat()
    except:
        pass

    # 无法解析，返回当前时间
    return datetime.now().isoformat()


def _generate_news_id(source: str, ticker: str, url: str) -> str:
    """
    生成稳定的news_id

    Args:
        source: 数据源
        ticker: 股票代码
        url: 新闻URL

    Returns:
        news_id
    """
    # 使用source + ticker + url的hash生成稳定ID
    content = f"{source}_{ticker}_{url}"
    hash_digest = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"{source}_{ticker}_{hash_digest}"


__all__ = ['normalize_ir_item']
