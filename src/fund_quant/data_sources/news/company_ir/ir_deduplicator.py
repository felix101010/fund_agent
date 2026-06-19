"""
Company IR新闻去重器
基于news_id、URL和标题去重
"""
import re
from urllib.parse import urlparse, parse_qs, urlencode


def normalize_url(url: str) -> str:
    """
    标准化URL用于去重

    Args:
        url: 原始URL

    Returns:
        标准化后的URL
    """
    try:
        parsed = urlparse(url)
        # 去掉协议差异
        netloc = parsed.netloc.lower().replace('www.', '')
        # 去掉尾部斜杠
        path = parsed.path.rstrip('/')
        # 保留关键query参数，去掉追踪参数
        query_params = parse_qs(parsed.query)
        # 过滤追踪参数
        filtered_params = {
            k: v for k, v in query_params.items()
            if k not in ['utm_source', 'utm_medium', 'utm_campaign', 'ref', 'source']
        }
        query = urlencode(sorted(filtered_params.items()), doseq=True) if filtered_params else ''
        
        normalized = f"{netloc}{path}"
        if query:
            normalized += f"?{query}"
        
        return normalized
    except:
        return url.lower()


def normalize_title(title: str) -> str:
    """
    标准化标题用于去重

    Args:
        title: 原始标题

    Returns:
        标准化后的标题
    """
    # 转小写
    normalized = title.lower()
    # 去除多余空白
    normalized = ' '.join(normalized.split())
    # 去除标点
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized


def deduplicate_ir_items(items: list[dict]) -> list[dict]:
    """
    去重IR新闻items

    Args:
        items: 原始item列表

    Returns:
        去重后的item列表
    """
    if not items:
        return []

    seen_news_ids = set()
    seen_urls = set()
    seen_title_keys = set()
    
    unique_items = []

    for item in items:
        # 1. 检查news_id
        news_id = item.get('news_id', '')
        if news_id and news_id in seen_news_ids:
            continue

        # 2. 检查URL
        url = item.get('url', '')
        if url:
            norm_url = normalize_url(url)
            if norm_url in seen_urls:
                continue

        # 3. 检查ticker + title + date
        ticker = item.get('ticker', '')
        title = item.get('title', '')
        publish_time = item.get('publish_time', '')
        publish_date = publish_time.split('T')[0] if 'T' in publish_time else publish_time[:10]
        
        if ticker and title:
            norm_title = normalize_title(title)
            title_key = f"{ticker}_{norm_title}_{publish_date}"
            if title_key in seen_title_keys:
                continue

        # 未重复，加入结果
        if news_id:
            seen_news_ids.add(news_id)
        if url:
            seen_urls.add(normalize_url(url))
        if ticker and title:
            seen_title_keys.add(title_key)

        unique_items.append(item)

    return unique_items


__all__ = ['deduplicate_ir_items', 'normalize_url', 'normalize_title']
