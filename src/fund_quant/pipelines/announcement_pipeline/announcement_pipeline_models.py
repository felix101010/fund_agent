"""
公告处理流程数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any


@dataclass
class AnnouncementProcessResult:
    """单条公告处理结果"""
    batch_id: str
    announcement_id: str
    stock_code: str
    stock_name: str
    title: str
    publish_time: Optional[datetime]
    url: str
    pdf_url: str
    announcement_type_raw: str
    announcement_type: str
    action: str
    need_ai: bool
    need_pdf: bool
    pre_score: int
    matched_keywords: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    # AI抽取结果
    final_event: Optional[dict] = None

    # 验证和后处理
    validation_errors: List[str] = field(default_factory=list)
    postprocess_notes: List[str] = field(default_factory=list)
    error_tags: List[str] = field(default_factory=list)

    # PDF解析状态（阶段2A新增）
    pdf_parsed: bool = False
    pdf_download_status: str = "not_required"  # not_required/pending/success/failed
    pdf_parse_status: str = "not_required"
    pdf_text_length: int = 0
    pdf_text_preview: str = ""
    pdf_parse_error: str = ""
    pdf_extraction_method: str = ""
    pdf_unparsed_score_cap: Optional[int] = None

    # 处理状态
    processing_status: str = "pending"  # pending/success/failed
    processing_error: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'batch_id': self.batch_id,
            'announcement_id': self.announcement_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'title': self.title,
            'publish_time': self.publish_time.isoformat() if self.publish_time else None,
            'url': self.url,
            'pdf_url': self.pdf_url,
            'announcement_type_raw': self.announcement_type_raw,
            'announcement_type': self.announcement_type,
            'action': self.action,
            'need_ai': self.need_ai,
            'need_pdf': self.need_pdf,
            'pre_score': self.pre_score,
            'matched_keywords': self.matched_keywords,
            'reasons': self.reasons,
            'final_event': self.final_event,
            'validation_errors': self.validation_errors,
            'postprocess_notes': self.postprocess_notes,
            'error_tags': self.error_tags,
            'pdf_parsed': self.pdf_parsed,
            'pdf_download_status': self.pdf_download_status,
            'pdf_parse_status': self.pdf_parse_status,
            'pdf_text_length': self.pdf_text_length,
            'pdf_text_preview': self.pdf_text_preview,
            'pdf_parse_error': self.pdf_parse_error,
            'pdf_extraction_method': self.pdf_extraction_method,
            'pdf_unparsed_score_cap': self.pdf_unparsed_score_cap,
            'processing_status': self.processing_status,
            'processing_error': self.processing_error
        }


@dataclass
class BatchAnnouncementResult:
    """批量公告处理结果"""
    batch_id: str
    total_fetched: int
    after_dedup: int
    new_count: int
    processed_count: int
    skipped_count: int
    need_ai_count: int
    need_pdf_count: int
    results: List[AnnouncementProcessResult] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'batch_id': self.batch_id,
            'total_fetched': self.total_fetched,
            'after_dedup': self.after_dedup,
            'new_count': self.new_count,
            'processed_count': self.processed_count,
            'skipped_count': self.skipped_count,
            'need_ai_count': self.need_ai_count,
            'need_pdf_count': self.need_pdf_count,
            'results': [r.to_dict() for r in self.results],
            'stats': self.stats,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


__all__ = ['AnnouncementProcessResult', 'BatchAnnouncementResult']
