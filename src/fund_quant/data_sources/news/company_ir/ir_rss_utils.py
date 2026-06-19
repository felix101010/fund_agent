"""
Company IR RSS工具函数
RSS feed自动发现和验证
"""
import logging
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

logger = logging.getLogger(__name__)


def is_probable_feed_response(content_type: str, text: str) -> bool:
    """
    判断响应是否是真实的RSS/Atom feed

    Args:
        content_type: HTTP Content-Type头
        text: 响应文本

    Returns:
        是否是feed
    """
    # 检查Content-Type
    content_type_lower = content_type.lower()
    feed_types = ['xml', 'rss', 'atom', 'application/rss', 'application/atom']
    if any(t in content_type_lower for t in feed_types):
        return True

    # 检查内容前500字符
    if not text:
        return False

    preview = text[:500].lower()
    feed_tags = ['<rss', '<feed', '<rdf:rdf', '<?xml']
    return any(tag in preview for tag in feed_tags)


def discover_feed_urls(html: str, base_url: str) -> list[str]:
    """
    从HTML中发现RSS feed链接

    Args:
        html: HTML内容
        base_url: 基础URL（用于解析相对路径）

    Returns:
        发现的feed URL列表
    """
    if BeautifulSoup is None:
        logger.warning("BeautifulSoup未安装，无法发现feed")
        return []

    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        logger.error(f"HTML解析失败: {e}")
        return []

    feed_urls = []

    # 1. 优先查找<link rel="alternate" type="application/rss+xml"> (最可靠)
    for link in soup.find_all('link', rel='alternate'):
        link_type = link.get('type', '').lower()
        if 'rss' in link_type or 'atom' in link_type:
            href = link.get('href')
            if href:
                absolute_url = urljoin(base_url, href)
                feed_urls.append(absolute_url)
                logger.debug(f"发现 <link rel=alternate> feed: {absolute_url}")

    # 2. 查找包含RSS/feed关键词的<a>链接 (更严格的过滤)
    for a in soup.find_all('a', href=True):
        href = a['href']
        href_lower = href.lower()
        text = a.get_text(strip=True).lower()

        # 必须匹配明确的feed模式
        if _is_feed_url(href_lower, text):
            absolute_url = urljoin(base_url, href)
            feed_urls.append(absolute_url)
            logger.debug(f"发现 <a> feed: {absolute_url}")

    # 3. 去重并保持顺序
    seen = set()
    unique_urls = []
    for url in feed_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


def _is_feed_url(href_lower: str, text_lower: str) -> bool:
    """
    判断链接是否是真正的feed URL (严格模式)

    Args:
        href_lower: 小写的链接URL
        text_lower: 小写的链接文本

    Returns:
        是否是feed URL
    """
    # 首先排除明确的非feed模式
    reject_patterns = [
        '/detail/',
        '/press-releases/detail/',
        '/news-events/press-releases/detail/',
        '/news/detail/',
        '/news-details/',
        '/press-release-detail/',
        'javascript:',
        'mailto:',
        '#',
        'email-alert',
        'contact',
        'privacy',
        'terms',
        'careers',
        'unsubscribe',
        'login',
        'signin'
    ]

    for pattern in reject_patterns:
        if pattern in href_lower or pattern in text_lower:
            return False

    # 必须匹配明确的feed模式
    feed_patterns_href = [
        '/rss',
        'rss-feed',
        '/feed',
        '.xml',
        'pagetemplate=rss',
        'output=rss',
        'releases.xml',
        'event.aspx',
        'news.xml',
        'rss.aspx'
    ]

    # 如果href匹配feed模式，返回True
    if any(pattern in href_lower for pattern in feed_patterns_href):
        return True

    # 如果是普通列表页(不是feed)，拒绝
    # 例如: /press-releases, /news-releases (没有/rss或.xml)
    if href_lower.endswith(('/press-releases', '/news-releases', '/news', '/news-events')):
        # 除非明确标记为feed
        if 'rss' not in href_lower and '.xml' not in href_lower:
            return False

    return False


__all__ = [
    'is_probable_feed_response',
    'discover_feed_urls'
]
