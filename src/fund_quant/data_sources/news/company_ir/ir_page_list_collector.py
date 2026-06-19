"""
Company IR Page List Collector
从HTML页面列表提取新闻链接（当RSS不可用时的fallback）
"""
import logging
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

logger = logging.getLogger(__name__)


class IRPageListCollector:
    """
    IR页面列表采集器

    职责：
    - 从HTML页面提取新闻列表
    - 支持常见IR页面结构（PR Newswire, Q4 Inc, etc.）
    - 返回原始item列表
    """

    def __init__(self):
        """初始化"""
        if requests is None:
            logger.warning("requests未安装，页面采集功能不可用")
        if BeautifulSoup is None:
            logger.warning("BeautifulSoup未安装，页面采集功能不可用")

    def collect_from_page(self, ticker: str, page_url: str, days: int = 30) -> List[dict]:
        """
        从页面列表采集新闻

        Args:
            ticker: 股票代码
            page_url: 页面URL
            days: 采集最近N天的新闻

        Returns:
            原始item列表
        """
        if requests is None or BeautifulSoup is None:
            logger.warning(f"依赖库未安装，跳过{ticker}页面采集")
            return []

        try:
            # 1. 请求页面
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }

            response = requests.get(page_url, headers=headers, timeout=20)
            response.raise_for_status()

            # 2. 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # 3. 提取新闻项
            items = self._extract_news_items(soup, page_url, ticker)

            # 4. 日期过滤
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_items = []

            for item in items:
                # 尝试解析日期
                if item.get('published'):
                    try:
                        pub_date = self._parse_date(item['published'])
                        if pub_date and pub_date < cutoff_date:
                            continue
                    except:
                        # 日期解析失败不丢弃，保留item但打印warning
                        logger.warning(f"日期解析失败: {item.get('published')}")

                filtered_items.append(item)

            logger.info(f"从{page_url}提取{len(filtered_items)}条新闻")
            return filtered_items

        except Exception as e:
            logger.error(f"页面采集失败: {page_url}, {e}")
            return []

    def _extract_news_items(self, soup: BeautifulSoup, base_url: str, ticker: str) -> List[dict]:
        """
        从soup中提取新闻项

        Args:
            soup: BeautifulSoup对象
            base_url: 基础URL
            ticker: 股票代码

        Returns:
            新闻项列表
        """
        items = []

        # 尝试多种选择器模式
        selectors = [
            # 通用article标签
            {'tag': 'article', 'class': None},
            # 常见新闻容器
            {'tag': 'div', 'class': 'press-release'},
            {'tag': 'div', 'class': 'news-item'},
            {'tag': 'div', 'class': 'news-release'},
            {'tag': 'div', 'class': 'module_item'},
            {'tag': 'div', 'class': 'wd_item'},
            # Q4 Inc IR平台
            {'tag': 'div', 'class': 'nir-widget'},
            {'tag': 'div', 'class': 'q4-press-release'},
            # 表格行
            {'tag': 'tr', 'class': None},
        ]

        for selector in selectors:
            if selector['class']:
                elements = soup.find_all(selector['tag'], class_=lambda x: x and selector['class'] in x)
            else:
                elements = soup.find_all(selector['tag'])

            if elements:
                logger.debug(f"使用选择器 {selector} 找到{len(elements)}个元素")
                for elem in elements:
                    item = self._parse_news_element(elem, base_url, ticker)
                    if item:
                        items.append(item)

                if items:
                    break  # 找到有效items就停止

        # 如果上述选择器都失败，尝试查找所有包含链接的元素
        if not items:
            logger.debug("使用fallback: 查找所有新闻链接")
            items = self._extract_from_links(soup, base_url, ticker)

        return items

    def _parse_news_element(self, elem, base_url: str, ticker: str) -> dict:
        """
        解析单个新闻元素

        Args:
            elem: BeautifulSoup元素
            base_url: 基础URL
            ticker: 股票代码

        Returns:
            新闻item或None
        """
        try:
            # 查找链接
            link_elem = elem.find('a', href=True)
            if not link_elem:
                return None

            href = link_elem['href']
            title = link_elem.get_text(strip=True)

            # 过滤无效链接
            if not self._is_valid_news_link(href, title):
                return None

            # 构建绝对URL
            url = urljoin(base_url, href)

            # 查找日期
            published = ''
            date_selectors = [
                {'tag': 'time'},
                {'tag': 'span', 'class': 'date'},
                {'tag': 'div', 'class': 'date'},
                {'tag': 'p', 'class': 'date'},
            ]

            for sel in date_selectors:
                if sel.get('class'):
                    date_elem = elem.find(sel['tag'], class_=lambda x: x and sel['class'] in x)
                else:
                    date_elem = elem.find(sel['tag'])

                if date_elem:
                    published = date_elem.get_text(strip=True)
                    break

            # 查找摘要
            summary = ''
            summary_elem = elem.find(['p', 'div'], class_=lambda x: x and ('summary' in x or 'description' in x))
            if summary_elem:
                summary = summary_elem.get_text(strip=True)

            return {
                'title': title,
                'link': url,
                'published': published,
                'summary': summary,
                'source_detail': 'ir_page_fallback'
            }

        except Exception as e:
            logger.debug(f"解析元素失败: {e}")
            return None

    def _extract_from_links(self, soup: BeautifulSoup, base_url: str, ticker: str) -> List[dict]:
        """
        从所有链接中提取新闻（fallback方法）

        Args:
            soup: BeautifulSoup对象
            base_url: 基础URL
            ticker: 股票代码

        Returns:
            新闻项列表
        """
        items = []

        for a in soup.find_all('a', href=True):
            href = a['href']
            href_lower = href.lower()
            text = a.get_text(strip=True)

            # 必须包含新闻相关关键词
            if not any(kw in href_lower for kw in ['press', 'news', 'release', 'detail']):
                continue

            # 过滤无效链接
            if not self._is_valid_news_link(href, text):
                continue

            url = urljoin(base_url, href)

            items.append({
                'title': text,
                'link': url,
                'published': '',
                'summary': '',
                'source_detail': 'ir_page_fallback'
            })

        return items

    def _is_valid_news_link(self, href: str, text: str) -> bool:
        """
        判断链接是否是有效的新闻链接

        Args:
            href: 链接URL
            text: 链接文本

        Returns:
            是否有效
        """
        href_lower = href.lower()
        text_lower = text.lower()

        # 排除无效链接
        invalid_patterns = [
            'privacy', 'contact', 'careers', 'email-alert',
            'javascript:', 'mailto:', '#',
            'sec-filings', 'stock-quote', 'financial-information',
            'investor-faqs', 'governance', 'events-and-presentations'
        ]

        for pattern in invalid_patterns:
            if pattern in href_lower or pattern in text_lower:
                return False

        # 标题不能为空或过短
        if not text or len(text) < 10:
            return False

        return True

    def _parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串

        Returns:
            datetime对象或None
        """
        if not date_str:
            return None

        # 尝试多种格式
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y/%m/%d'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue

        # 尝试email格式
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            pass

        return None


__all__ = ['IRPageListCollector']
