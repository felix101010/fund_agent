"""
公告去重器
"""
from typing import List, Set
from fund_quant.data_sources.announcements.announcement_models import RawAnnouncement


class AnnouncementDeduplicator:
    """
    公告去重器

    基于announcement_id去重
    """

    def __init__(self):
        """初始化去重器"""
        self.seen_ids: Set[str] = set()

    def deduplicate(self, announcements: List[RawAnnouncement]) -> List[RawAnnouncement]:
        """
        去重公告列表

        Args:
            announcements: 原始公告列表

        Returns:
            去重后的公告列表
        """
        deduplicated = []

        for announcement in announcements:
            if announcement.announcement_id not in self.seen_ids:
                self.seen_ids.add(announcement.announcement_id)
                deduplicated.append(announcement)

        return deduplicated

    def mark_seen(self, announcement_id: str):
        """标记为已见"""
        self.seen_ids.add(announcement_id)

    def is_seen(self, announcement_id: str) -> bool:
        """检查是否已见"""
        return announcement_id in self.seen_ids

    def clear(self):
        """清空去重记录"""
        self.seen_ids.clear()


__all__ = ['AnnouncementDeduplicator']
