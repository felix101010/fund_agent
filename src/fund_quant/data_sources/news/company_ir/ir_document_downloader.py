"""
Company IR文档下载器
下载PDF等附件到本地
"""
import logging
from pathlib import Path
from typing import List

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class IRDocumentDownloader:
    """
    IR文档下载器

    职责：
    - 下载PDF文档
    - 保存到指定目录
    - 跳过webcast/video
    """

    def __init__(self, base_dir: str = "data/company_ir"):
        """
        初始化

        Args:
            base_dir: 基础保存目录
        """
        self.base_dir = Path(base_dir)
        if requests is None:
            logger.warning("requests未安装，文档下载功能不可用")

    def download_attachments(
        self,
        ticker: str,
        publish_date: str,
        attachments: List[dict]
    ) -> List[dict]:
        """
        下载附件

        Args:
            ticker: 股票代码
            publish_date: 发布日期（用于组织目录）
            attachments: 附件列表

        Returns:
            下载结果列表
        """
        if requests is None:
            return []

        results = []

        # 创建保存目录
        # publish_date格式如：2024-01-15T10:30:00
        date_str = publish_date.split('T')[0] if 'T' in publish_date else publish_date[:10]
        save_dir = self.base_dir / ticker.upper() / date_str
        save_dir.mkdir(parents=True, exist_ok=True)

        for attachment in attachments:
            att_type = attachment.get('type', 'unknown')
            url = attachment.get('url', '')
            title = attachment.get('title', 'document')

            # 第一版只下载PDF
            if att_type != 'pdf':
                results.append({
                    'url': url,
                    'local_path': '',
                    'type': att_type,
                    'status': 'skipped',
                    'error': f'{att_type}类型暂不下载'
                })
                continue

            # 下载PDF
            try:
                result = self._download_pdf(url, save_dir, title)
                results.append(result)

            except Exception as e:
                logger.error(f"下载失败: {url}, {e}")
                results.append({
                    'url': url,
                    'local_path': '',
                    'type': att_type,
                    'status': 'failed',
                    'error': str(e)
                })

        return results

    def _download_pdf(self, url: str, save_dir: Path, title: str) -> dict:
        """
        下载单个PDF

        Args:
            url: PDF URL
            save_dir: 保存目录
            title: 文件标题

        Returns:
            下载结果
        """
        # 生成文件名
        filename = self._sanitize_filename(title)
        if not filename.endswith('.pdf'):
            filename += '.pdf'

        file_path = save_dir / filename

        # 如果已存在，跳过
        if file_path.exists():
            logger.info(f"文件已存在，跳过: {file_path}")
            return {
                'url': url,
                'local_path': str(file_path),
                'type': 'pdf',
                'status': 'exists',
                'error': ''
            }

        # 下载
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # 保存
        with open(file_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"下载成功: {file_path}")

        return {
            'url': url,
            'local_path': str(file_path),
            'type': 'pdf',
            'status': 'success',
            'error': ''
        }

    def _sanitize_filename(self, title: str) -> str:
        """清理文件名"""
        # 移除非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '_')

        # 限制长度
        if len(title) > 100:
            title = title[:100]

        return title.strip()


__all__ = ['IRDocumentDownloader']
