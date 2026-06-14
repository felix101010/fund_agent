"""
Filing 下载器
下载filing正文，清洗HTML，转纯文本
"""
from typing import Optional
from bs4 import BeautifulSoup
import re

from fund_quant.data_sources.sec_edgar.sec_client import SECClient
from fund_quant.data_sources.sec_edgar.sec_config import CONTENT_MIN_LENGTH, CONTENT_MAX_LENGTH


class FilingDownloader:
    """
    Filing 下载器

    职责：
    1. 下载filing正文
    2. HTML转纯文本
    3. 清洗和标准化
    4. 截断到指定长度
    """

    def __init__(self, sec_client: SECClient = None):
        """
        初始化

        Args:
            sec_client: SEC客户端
        """
        self.sec_client = sec_client or SECClient()

    def download_and_parse(self, filing_url: str) -> Optional[str]:
        """
        下载并解析filing

        Args:
            filing_url: Filing URL

        Returns:
            清洗后的纯文本，失败返回None
        """
        # 下载
        raw_content = self.sec_client.download_filing(filing_url)
        if not raw_content:
            return None

        # 清洗HTML
        text = self._clean_html(raw_content)

        # 检查最小长度
        if len(text) < CONTENT_MIN_LENGTH:
            return None

        # 截断
        text = self._truncate_content(text, CONTENT_MAX_LENGTH)

        return text

    def _clean_html(self, html_content: str) -> str:
        """
        清洗HTML，转纯文本

        Args:
            html_content: HTML内容

        Returns:
            纯文本
        """
        try:
            # 使用BeautifulSoup解析
            soup = BeautifulSoup(html_content, 'lxml')

            # 移除script和style标签
            for tag in soup(['script', 'style', 'meta', 'link']):
                tag.decompose()

            # 提取文本
            text = soup.get_text(separator=' ', strip=True)

            # 清理空白字符
            text = self._clean_whitespace(text)

            return text

        except Exception as e:
            # 如果BeautifulSoup失败，使用简单方法
            return self._simple_clean(html_content)

    def _simple_clean(self, html_content: str) -> str:
        """
        简单清洗（BeautifulSoup失败时的fallback）

        Args:
            html_content: HTML内容

        Returns:
            纯文本
        """
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', ' ', html_content)

        # 解码HTML实体
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')

        # 清理空白字符
        text = self._clean_whitespace(text)

        return text

    def _clean_whitespace(self, text: str) -> str:
        """
        清理空白字符

        Args:
            text: 文本

        Returns:
            清理后的文本
        """
        # 替换多个空白字符为单个空格
        text = re.sub(r'\s+', ' ', text)

        # 移除首尾空白
        text = text.strip()

        return text

    def _truncate_content(self, text: str, max_length: int) -> str:
        """
        截断内容

        Args:
            text: 文本
            max_length: 最大长度

        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text

        # 截断并添加提示
        truncated = text[:max_length]
        truncated += f"\n\n[Content truncated at {max_length} characters]"

        return truncated


__all__ = ['FilingDownloader']
