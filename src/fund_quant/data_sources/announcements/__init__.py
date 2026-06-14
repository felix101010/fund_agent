"""
公告数据源模块
"""
from fund_quant.data_sources.announcements.announcement_models import RawAnnouncement
from fund_quant.data_sources.announcements.cninfo_collector import CninfoCollector
from fund_quant.data_sources.announcements.announcement_deduplicator import AnnouncementDeduplicator
from fund_quant.data_sources.announcements.announcement_type_rules import (
    ROUTINE_GOVERNANCE_KEYWORDS,
    MEETING_NOTICE_KEYWORDS,
    RISK_KEYWORDS,
    HIGH_VALUE_KEYWORDS,
    WATCH_KEYWORDS,
    classify_announcement_type
)

__all__ = [
    'RawAnnouncement',
    'CninfoCollector',
    'AnnouncementDeduplicator',
    'ROUTINE_GOVERNANCE_KEYWORDS',
    'MEETING_NOTICE_KEYWORDS',
    'RISK_KEYWORDS',
    'HIGH_VALUE_KEYWORDS',
    'WATCH_KEYWORDS',
    'classify_announcement_type'
]
