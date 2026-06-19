"""
Company IR页面采集器
使用requests和BeautifulSoup解析IR新闻页面
"""
import logging
from typing import List

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

logger = logging.getLogger(__name__)


class IRPageCollector:
    """
    IR页面采集器

    职责：
    - 获取新闻页面正文
    - 提取PDF/presentation链接
    - 过滤无关内容
    """

    def __init__(self, timeout: int = 20):
        """
        初始化

        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        if requests is None or BeautifulSoup is None:
            logger.warning("requests或beautifulsoup4未安装，页面采集功能不可用")

    def fetch_article(self, url: str) -> dict:
        """
        获取文章详情

        Args:
            url: 文章URL

        Returns:
            {
                'content': '正文内容',
                'title': '页面标题',
                'attachments': [...],
                'error': '',
                'content_len': 0,
                'debug_html_path': ''  # 如果失败时保存的debug文件
            }
        """
        if requests is None or BeautifulSoup is None:
            return {
                'content': '',
                'title': '',
                'attachments': [],
                'error': 'requests或beautifulsoup4未安装',
                'content_len': 0,
                'debug_html_path': ''
            }

        try:
            # 请求页面
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # 处理编码问题
            # 优先使用apparent_encoding
            if response.apparent_encoding:
                response.encoding = response.apparent_encoding

            # 尝试用html.parser解析
            soup = None
            parse_error = None

            try:
                soup = BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                parse_error = str(e)
                logger.warning(f"html.parser失败: {e}, 尝试lxml")

                # 尝试lxml
                try:
                    soup = BeautifulSoup(response.content, 'lxml')
                except Exception as e2:
                    logger.error(f"lxml也失败: {e2}")
                    return {
                        'content': '',
                        'title': '',
                        'attachments': [],
                        'error': f'解析失败: {parse_error}',
                        'content_len': 0,
                        'debug_html_path': ''
                    }

            # 提取标题
            title = self._extract_title(soup)

            # 检查是否为 Apple Newsroom
            is_apple_newsroom = 'apple.com/newsroom' in url

            # 提取正文
            content = self._extract_content(soup, url, is_apple_newsroom)

            # 提取附件
            attachments = self._extract_attachments(soup, url)

            # 检查正文长度
            content_len = len(content)
            debug_html_path = ''

            if content_len < 200:
                logger.warning(f"正文长度过短 ({content_len}): {url}")

                # 保存debug HTML
                debug_html_path = self._save_debug_html(url, response.content)

            return {
                'content': content,
                'title': title,
                'attachments': attachments,
                'error': '' if content_len >= 200 else 'failed_short_content',
                'content_len': content_len,
                'debug_html_path': debug_html_path
            }

        except requests.exceptions.Timeout:
            logger.warning(f"请求超时: {url}")
            return {'content': '', 'title': '', 'attachments': [], 'error': 'Timeout', 'content_len': 0, 'debug_html_path': ''}

        except requests.exceptions.RequestException as e:
            logger.warning(f"请求失败: {url}, {e}")
            return {'content': '', 'title': '', 'attachments': [], 'error': str(e), 'content_len': 0, 'debug_html_path': ''}

        except Exception as e:
            logger.error(f"解析页面失败: {url}, {e}")
            return {'content': '', 'title': '', 'attachments': [], 'error': str(e), 'content_len': 0}

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取页面标题"""
        # 优先使用h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        # fallback到title标签
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)

        return ''

    def _extract_content(self, soup: BeautifulSoup, url: str = '', is_apple_newsroom: bool = False) -> str:
        """提取正文内容"""
        # 移除无关标签
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'noscript']):
            tag.decompose()

        # 尝试找主要内容区域
        main_content = None

        # Apple Newsroom 专用选择器（优先级最高）
        if is_apple_newsroom:
            apple_selectors = [
                '[data-analytics-region="article body"]',
                '.article-content',
                '.pagebody',
                '.page-body',
                '.pagebody-copy',
                '.article-body',
                '.newsroom',
                '.section-content',
            ]

            for selector in apple_selectors:
                if selector.startswith('['):
                    main_content = soup.select_one(selector)
                elif selector.startswith('.'):
                    main_content = soup.find(class_=lambda x: x and selector[1:] in x)
                else:
                    main_content = soup.find(selector)

                if main_content:
                    logger.debug(f"使用Apple Newsroom选择器: {selector}")
                    break

        # 常见的内容区域选择器（优先级从高到低）
        if not main_content:
            content_selectors = [
                '#news-release',
                '.news-release',
                '.press-release',
                '.release',
                'article',
                'main',
                '.wd_news_body',
                '.wd_body',
                '.wd_item',
                '.module_body',
                '.body',
                '.field--name-body',
                '.body-content',
                '.nir-widget',
                '.q4-press-release',
                '.pane-node-body',
                '[role="main"]',
                '.article-body',
                '.press-release-body',
                '.news-content',
                '#content',
                '.content',
                '.detail-content',
                '.release-body'
            ]

            for selector in content_selectors:
                if selector.startswith('.'):
                    # class选择器
                    main_content = soup.find(class_=lambda x: x and selector[1:] in x)
                elif selector.startswith('#'):
                    # id选择器
                    main_content = soup.find(id=selector[1:])
                elif selector.startswith('['):
                    # 属性选择器
                    main_content = soup.select_one(selector)
                else:
                    # 标签选择器
                    main_content = soup.find(selector)

                if main_content:
                    logger.debug(f"使用选择器: {selector}")
                    break

        # 如果没找到，使用智能fallback
        if not main_content:
            main_content = self._find_content_block_smart(soup, url, is_apple_newsroom)

        if main_content:
            # 提取文本，保留段落结构，支持table
            paragraphs = []

            # 提取标题和正文（包括table）
            for elem in main_content.find_all(['p', 'h1', 'h2', 'h3', 'li', 'td', 'th']):
                text = elem.get_text(strip=True)
                # 过滤太短的段落
                if len(text) > 20:
                    paragraphs.append(text)

            # 特殊处理table（提取完整表格文本）
            for table in main_content.find_all('table'):
                table_text = self._extract_table_text(table)
                if len(table_text) > 50:
                    paragraphs.append(table_text)

            content = '\n\n'.join(paragraphs)

            # 清洗连续空白
            import re
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = re.sub(r'  +', ' ', content)
            # 清理常见乱码
            content = content.replace('\xa0', ' ')
            content = content.replace('​', '')

            # 过滤常见的无关内容（Apple Newsroom 使用宽松规则）
            if self._is_low_value_content(content, is_apple_newsroom):
                logger.warning("检测到低价值内容")
                return ''

            return content

        return ''

    def _find_content_block_smart(self, soup: BeautifulSoup, url: str, is_apple_newsroom: bool = False):
        """智能查找内容块（fallback）"""
        # Apple Newsroom fallback: 提取所有 p 标签
        if is_apple_newsroom:
            apple_keywords = [
                'apple', 'siri', 'apple intelligence', 'app store',
                'ios', 'ipados', 'macos', 'developer', 'iphone',
                'ipad', 'mac', 'watch', 'vision', 'airpods'
            ]

            paragraphs = []
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) < 20:
                    continue

                text_lower = text.lower()
                # 保留包含Apple相关关键词的段落
                if any(kw in text_lower for kw in apple_keywords):
                    paragraphs.append(text)

            if paragraphs and len(paragraphs) >= 3:
                # 组成一个虚拟的content block
                from bs4 import BeautifulSoup as BS
                virtual_html = '<div>' + ''.join(f'<p>{p}</p>' for p in paragraphs) + '</div>'
                return BS(virtual_html, 'html.parser').find('div')

        # Lam Research 和其他PR页面的关键词
        keywords = [
            'reports financial results',
            'quarter',
            'revenue',
            'gaap',
            'non-gaap',
            'conference call',
            'net income',
            'earnings per share',
            'press release',
            'announces'
        ]

        max_score = 0
        best_block = None

        for div in soup.find_all(['div', 'section', 'article']):
            # 跳过导航、菜单等
            div_class = ' '.join(div.get('class', [])).lower()
            if any(skip in div_class for skip in ['nav', 'menu', 'header', 'footer', 'sidebar']):
                continue

            text = div.get_text(strip=True).lower()
            text_len = len(text)

            # 计算得分：长度 + 关键词匹配
            score = text_len
            for keyword in keywords:
                if keyword in text:
                    score += 1000

            if score > max_score:
                max_score = score
                best_block = div

        return best_block

    def _extract_table_text(self, table) -> str:
        """提取table文本"""
        rows = []
        for tr in table.find_all('tr'):
            cells = []
            for cell in tr.find_all(['td', 'th']):
                text = cell.get_text(strip=True)
                if text:
                    cells.append(text)
            if cells:
                rows.append(' | '.join(cells))

        return '\n'.join(rows)

    def _save_debug_html(self, url: str, content: bytes) -> str:
        """保存debug HTML文件"""
        try:
            from pathlib import Path
            import hashlib

            # 创建debug目录
            debug_dir = Path('debug/company_ir_failed_pages')
            debug_dir.mkdir(parents=True, exist_ok=True)

            # 从URL提取ticker
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.hostname or 'unknown'

            # 生成文件名
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{hostname}_{url_hash}.html"
            filepath = debug_dir / filename

            # 保存HTML
            with open(filepath, 'wb') as f:
                f.write(content)

            logger.info(f"保存debug HTML: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"保存debug HTML失败: {e}")
            return ''

    def _extract_attachments(self, soup: BeautifulSoup, base_url: str) -> List[dict]:
        """提取附件链接"""
        attachments = []

        # 查找所有链接
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)

            # PDF
            if href.endswith('.pdf') or 'pdf' in href.lower():
                attachments.append({
                    'type': 'pdf',
                    'title': text or 'PDF Document',
                    'url': self._make_absolute_url(href, base_url)
                })

            # Presentation (PPT/PPTX)
            elif href.endswith(('.ppt', '.pptx')) or 'presentation' in text.lower():
                attachments.append({
                    'type': 'presentation',
                    'title': text or 'Presentation',
                    'url': self._make_absolute_url(href, base_url)
                })

            # Webcast
            elif 'webcast' in href.lower() or 'webcast' in text.lower():
                attachments.append({
                    'type': 'webcast',
                    'title': text or 'Webcast',
                    'url': self._make_absolute_url(href, base_url)
                })

        return attachments

    def _make_absolute_url(self, url: str, base_url: str) -> str:
        """转换为绝对URL"""
        if url.startswith('http'):
            return url

        from urllib.parse import urljoin
        return urljoin(base_url, url)

    def _is_low_value_content(self, content: str, is_apple_newsroom: bool = False) -> bool:
        """判断是否为低价值内容"""
        content_lower = content.lower()

        # Apple Newsroom 使用宽松规则
        if is_apple_newsroom:
            # 太短
            if len(content) < 50:
                return True

            # 只包含导航、隐私等无关内容，但不包含实质内容
            apple_substance_keywords = [
                'apple intelligence', 'siri', 'app store', 'ios',
                'ipados', 'developer', 'iphone', 'ipad', 'mac'
            ]

            has_substance = any(kw in content_lower for kw in apple_substance_keywords)

            # 如果包含实质关键词，不认为是低价值
            if has_substance:
                return False

            # 如果太短且没有实质内容，才认为是低价值
            if len(content) < 200:
                return True

            return False

        # 普通页面的规则
        # 太短
        if len(content) < 100:
            return True

        # 只包含联系信息
        low_value_keywords = ['contact', 'media contact', 'investor relations contact']
        if all(keyword in content_lower for keyword in low_value_keywords) and len(content) < 300:
            return True

        return False


__all__ = ['IRPageCollector']
