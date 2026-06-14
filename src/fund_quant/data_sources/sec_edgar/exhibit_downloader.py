"""
Exhibit 下载器
下载index.json并下载重要附件
"""
from typing import List, Dict, Any, Optional
import json

from fund_quant.data_sources.sec_edgar.sec_client import SECClient
from fund_quant.data_sources.sec_edgar.url_builder import SECURLBuilder
from fund_quant.data_sources.sec_edgar.exhibit_parser import ExhibitParser
from fund_quant.data_sources.sec_edgar.filing_downloader import FilingDownloader


class ExhibitDownloader:
    """
    Exhibit 下载器

    职责：
    1. 下载index.json
    2. 解析重要附件列表
    3. 下载附件正文
    4. 清洗HTML
    """

    def __init__(self, sec_client: SECClient = None, filing_downloader: FilingDownloader = None):
        """
        初始化

        Args:
            sec_client: SEC客户端
            filing_downloader: Filing下载器（复用HTML清洗逻辑）
        """
        self.sec_client = sec_client or SECClient()
        self.filing_downloader = filing_downloader or FilingDownloader()

    def download_exhibits(
        self,
        cik: str,
        accession_number: str,
        max_exhibits: int = 5
    ) -> List[Dict[str, Any]]:
        """
        下载重要附件

        Args:
            cik: CIK
            accession_number: Accession number
            max_exhibits: 最大下载数量

        Returns:
            附件列表 [{type, filename, description, url, text, content_len, download_status, error}]
        """
        exhibits = []

        try:
            # 1. 下载index.json
            index_json = self._download_index_json(cik, accession_number)
            if not index_json:
                return exhibits

            # 2. 解析附件列表
            exhibit_metadata = ExhibitParser.parse_index_json(
                index_json, cik, accession_number
            )

            if not exhibit_metadata:
                return exhibits

            # 3. 下载附件正文（限制数量）
            for metadata in exhibit_metadata[:max_exhibits]:
                exhibit = self._download_single_exhibit(metadata)
                exhibits.append(exhibit)

        except Exception as e:
            print(f"⚠️  下载exhibits失败: {str(e)}")

        return exhibits

    def _download_index_json(self, cik: str, accession_number: str) -> Optional[Dict[str, Any]]:
        """
        下载index.json

        Args:
            cik: CIK
            accession_number: Accession number

        Returns:
            index.json内容，失败返回None
        """
        try:
            url = SECURLBuilder.build_index_json_url(cik, accession_number)

            # 使用统一封装的get_json方法
            return self.sec_client.get_json(url)

        except Exception as e:
            print(f"⚠️  下载index.json失败 (CIK={cik}): {str(e)}")
            return None

    def _download_single_exhibit(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        下载单个附件

        Args:
            metadata: 附件元数据

        Returns:
            附件信息（含正文）
        """
        exhibit = {
            'type': metadata.get('type', ''),
            'filename': metadata.get('filename', ''),
            'description': metadata.get('description', ''),
            'url': metadata.get('url', ''),
            'text': '',
            'content_len': 0,
            'download_status': 'pending',
            'error': ''
        }

        try:
            # 下载并清洗（使用统一方法）
            url = metadata.get('url', '')
            raw_content = self.sec_client.get_text(url)

            if not raw_content:
                exhibit['download_status'] = 'failed'
                exhibit['error'] = '下载失败'
                return exhibit

            # 清洗HTML
            text = self.filing_downloader._clean_html(raw_content)

            exhibit['text'] = text
            exhibit['content_len'] = len(text)
            exhibit['download_status'] = 'success'

        except Exception as e:
            exhibit['download_status'] = 'failed'
            exhibit['error'] = str(e)

        return exhibit


__all__ = ['ExhibitDownloader']
