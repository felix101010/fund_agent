"""
巨潮资讯PDF下载器（简化版 - 只负责下载）
"""
import os
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional


class CninfoPdfDownloader:
    """
    巨潮资讯PDF下载器

    职责：只负责下载PDF，不做业务判断
    是否下载的决策由SingleAnnouncementPipeline.should_parse_pdf()控制
    """

    def __init__(self, output_dir: str = "data/raw/cninfo_pdfs"):
        """
        初始化

        Args:
            output_dir: PDF保存目录
        """
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download(
        self,
        announcement_id: str,
        pdf_url: str,
        publish_time=None
    ) -> dict:
        """
        下载PDF

        Args:
            announcement_id: 公告ID
            pdf_url: PDF URL
            publish_time: 发布时间（用于组织目录）

        Returns:
            {
                'status': 'success/failed',
                'local_path': '...',
                'error': '...'
            }
        """
        if not pdf_url:
            return {
                'status': 'failed',
                'local_path': '',
                'error': 'PDF URL为空'
            }

        # 创建保存路径
        date_str = datetime.now().strftime('%Y%m%d')
        save_dir = Path(self.output_dir) / date_str
        save_dir.mkdir(parents=True, exist_ok=True)

        file_path = save_dir / f"{announcement_id}.pdf"

        # 如果已存在，跳过
        if file_path.exists():
            return {
                'status': 'success',
                'local_path': str(file_path),
                'error': ''
            }

        # 下载
        try:
            response = self.session.get(pdf_url, timeout=20)

            if response.status_code != 200:
                return {
                    'status': 'failed',
                    'local_path': '',
                    'error': f'HTTP {response.status_code}'
                }

            # 保存
            with open(file_path, 'wb') as f:
                f.write(response.content)

            return {
                'status': 'success',
                'local_path': str(file_path),
                'error': ''
            }

        except requests.exceptions.Timeout:
            return {
                'status': 'failed',
                'local_path': '',
                'error': 'Download timeout'
            }
        except Exception as e:
            return {
                'status': 'failed',
                'local_path': '',
                'error': str(e)
            }

    # Deprecated: 下载决策由Pipeline控制
    def should_download(self, action: str, need_pdf: bool) -> bool:
        """
        DEPRECATED: 下载决策现在由SingleAnnouncementPipeline.should_parse_pdf()控制
        本方法保留仅用于向后兼容，不应被调用
        """
        return action in ["analyze", "risk_review"] and need_pdf


__all__ = ['CninfoPdfDownloader']
