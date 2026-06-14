"""
公告数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawAnnouncement:
    """原始公告数据"""
    announcement_id: str
    source: str = "cninfo"
    stock_code: str = ""
    stock_name: str = ""
    title: str = ""
    announcement_type_raw: str = ""
    publish_time: Optional[datetime] = None
    url: str = ""
    pdf_url: str = ""
    content: str = ""
    file_path: str = ""
    created_at: Optional[datetime] = None

    def to_dict(self):
        """转换为字典"""
        return {
            'announcement_id': self.announcement_id,
            'source': self.source,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'title': self.title,
            'announcement_type_raw': self.announcement_type_raw,
            'publish_time': self.publish_time.isoformat() if self.publish_time else None,
            'url': self.url,
            'pdf_url': self.pdf_url,
            'content': self.content,
            'file_path': self.file_path,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


__all__ = ['RawAnnouncement']
