"""
公告过滤器
基于公告类型和关键词决定处理策略
"""
from typing import Any
from dataclasses import dataclass, field
from fund_quant.data_sources.announcements.announcement_type_rules import classify_announcement_type


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


@dataclass
class AnnouncementFilterResult:
    """公告过滤结果"""
    announcement_id: str
    action: str  # analyze / risk_review / archive / watch
    need_ai: bool
    need_pdf: bool
    pre_score: int
    announcement_type: str
    matched_keywords: list = field(default_factory=list)
    reasons: list = field(default_factory=list)


class AnnouncementFilter:
    """
    公告过滤器

    职责：
    1. 根据公告类型决定处理策略
    2. 判断是否需要AI分析
    3. 判断是否需要下载PDF
    4. 给出预评分
    """

    def filter(self, announcement: Any) -> AnnouncementFilterResult:
        """
        过滤公告

        Args:
            announcement: RawAnnouncement对象

        Returns:
            AnnouncementFilterResult
        """
        announcement_id = get_field(announcement, 'announcement_id', '')
        title = get_field(announcement, 'title', '')
        announcement_type_raw = get_field(announcement, 'announcement_type_raw', '')

        # 分类
        classification = classify_announcement_type(title, announcement_type_raw)

        announcement_type = classification['announcement_type']
        category = classification['category']
        pre_score = classification['pre_score']
        matched_keyword = classification['matched_keyword']
        priority = classification.get('priority', 'P4')

        matched_keywords = [matched_keyword] if matched_keyword else []
        reasons = []

        # 根据分类决定策略
        if category == 'routine':
            # P0: 流程/制度/治理类
            action = 'archive'
            need_ai = False
            need_pdf = False
            reasons.append(f"流程/治理类公告（{matched_keyword}），归档")

        elif category == 'risk':
            # P1: 真实风险类
            action = 'risk_review'
            need_ai = True
            need_pdf = True
            reasons.append(f"风险公告（{matched_keyword}），需风险审查")

        elif category == 'business':
            # P2: 真实经营类
            action = 'analyze'
            need_ai = True
            need_pdf = True
            reasons.append(f"经营类公告（{matched_keyword}），需分析")

        elif category == 'watch':
            # P3: 权益/观察类
            action = 'watch'
            # 股权转让/资产出售/对外担保需要AI
            if announcement_type in ['asset_or_equity_transfer', 'external_guarantee']:
                need_ai = True
            else:
                need_ai = False
            need_pdf = True if pre_score >= 50 else False
            reasons.append(f"观察类公告（{matched_keyword}），关注")

        else:
            # P4: 未知类
            action = 'watch'
            need_ai = False
            need_pdf = False
            reasons.append("未分类公告，低优先级观察")

        return AnnouncementFilterResult(
            announcement_id=announcement_id,
            action=action,
            need_ai=need_ai,
            need_pdf=need_pdf,
            pre_score=pre_score,
            announcement_type=announcement_type,
            matched_keywords=matched_keywords,
            reasons=reasons
        )


__all__ = ['AnnouncementFilter', 'AnnouncementFilterResult']
