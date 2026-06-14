"""
SEC 事件规则分类器
根据form_type/items/keywords判断action/need_ai/pre_score
"""
from typing import Dict, Any, List

from fund_quant.data_sources.sec_edgar.sec_rules_config import (
    SEC_8K_ITEM_EVENT_MAP,
    SEC_8K_ITEM_PRIORITY,
    EXECUTIVE_KEYWORDS,
    RISK_KEYWORDS
)


class SECEventRules:
    """
    SEC 事件规则分类器

    职责：
    根据filing的form_type、items、content判断
    - action (analyze/archive/retry_or_archive)
    - need_ai (true/false)
    - pre_score (0-100)
    - event_hint (事件类型提示)
    - reason (判断理由)
    - risk_flags (风险标记)
    """

    @staticmethod
    def classify_sec_filing(filing: Dict[str, Any]) -> Dict[str, Any]:
        """
        分类SEC filing

        Args:
            filing: {
                form_type: str,
                content: str,
                items: list[str],
                download_status: str,
                has_exhibits: bool
            }

        Returns:
            {
                action: str,
                need_ai: bool,
                pre_score: int,
                event_hint: str,
                reason: str,
                risk_flags: list[str]
            }
        """
        result = {
            "action": "archive",
            "need_ai": False,
            "pre_score": 0,
            "event_hint": "",
            "reason": "",
            "risk_flags": []
        }

        # 1. 检查下载状态和内容
        if not SECEventRules._validate_content(filing, result):
            return result

        # 2. 获取基础信息
        form_type = filing.get('form_type', '')
        items = filing.get('items', [])
        content = filing.get('content', '')

        # 3. 处理8-K
        if form_type in ['8-K', '8-K/A']:
            SECEventRules._classify_8k(items, content, result)

        # 4. 提取风险标记
        result['risk_flags'] = SECEventRules._extract_risk_flags(content, items)

        return result

    @staticmethod
    def _validate_content(filing: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        验证内容是否有效

        Args:
            filing: filing数据
            result: 结果字典（会被修改）

        Returns:
            是否有效
        """
        download_status = filing.get('download_status', '')
        content = filing.get('content', '')

        # 下载失败
        if download_status == 'failed':
            result['action'] = 'retry_or_archive'
            result['reason'] = '下载失败'
            return False

        # 内容为空
        if not content:
            result['action'] = 'retry_or_archive'
            result['reason'] = '内容为空'
            return False

        # 内容过短
        if len(content) < 100:
            result['action'] = 'retry_or_archive'
            result['reason'] = f'内容过短（{len(content)}字符）'
            return False

        return True

    @staticmethod
    def _classify_8k(items: List[str], content: str, result: Dict[str, Any]):
        """
        分类8-K filing

        Args:
            items: Item列表
            content: 正文
            result: 结果字典（会被修改）
        """
        # 默认8-K需要分析
        result['action'] = 'analyze'
        result['need_ai'] = True

        # 没有Item
        if not items:
            result['pre_score'] = 60
            result['event_hint'] = 'general_8k'
            result['reason'] = '8-K未识别到具体Item，默认需要AI分析'
            return

        # 只有Item 9.01（仅附件）
        if items == ['9.01']:
            result['pre_score'] = 40
            result['event_hint'] = 'exhibits_only'
            result['need_ai'] = False  # 仅附件默认不需要AI
            result['reason'] = '8-K仅命中Item 9.01，主要是附件说明，交易价值较低'
            return

        # 多个Item：选择优先级最高的
        best_item = SECEventRules._get_highest_priority_item(items)
        priority = SEC_8K_ITEM_PRIORITY.get(best_item, 50)
        event_type = SEC_8K_ITEM_EVENT_MAP.get(best_item, 'general_8k')

        result['pre_score'] = priority
        result['event_hint'] = event_type
        result['reason'] = SECEventRules._build_reason(best_item, items)

    @staticmethod
    def _get_highest_priority_item(items: List[str]) -> str:
        """
        获取优先级最高的Item

        Args:
            items: Item列表

        Returns:
            优先级最高的Item
        """
        if not items:
            return ""

        # 按优先级排序
        sorted_items = sorted(
            items,
            key=lambda x: SEC_8K_ITEM_PRIORITY.get(x, 0),
            reverse=True
        )

        return sorted_items[0]

    @staticmethod
    def _build_reason(primary_item: str, all_items: List[str]) -> str:
        """
        构建判断理由

        Args:
            primary_item: 主要Item
            all_items: 所有Item

        Returns:
            理由文本
        """
        event_type = SEC_8K_ITEM_EVENT_MAP.get(primary_item, 'unknown')

        # 特殊Item的说明
        reason_map = {
            '2.02': '8-K命中Item 2.02，属于经营业绩/财报披露',
            '5.02': '8-K命中Item 5.02，属于董事或高管变动',
            '1.01': '8-K命中Item 1.01，属于重大协议签订',
            '2.01': '8-K命中Item 2.01，属于并购交易完成',
            '3.01': '8-K命中Item 3.01，属于退市风险警示',
            '2.06': '8-K命中Item 2.06，属于资产减值',
            '3.02': '8-K命中Item 3.02，属于融资事项',
            '8.01': '8-K命中Item 8.01，属于其他重大事件',
        }

        base_reason = reason_map.get(primary_item, f'8-K命中Item {primary_item}')

        # 如果有多个Item
        if len(all_items) > 1:
            base_reason += f'（同时包含Item {", ".join(all_items)}）'

        return base_reason

    @staticmethod
    def _extract_risk_flags(content: str, items: List[str]) -> List[str]:
        """
        提取风险标记

        Args:
            content: 正文
            items: Item列表

        Returns:
            风险标记列表
        """
        risk_flags = []
        content_lower = content.lower()

        # 检查风险关键词
        for keyword, flag in RISK_KEYWORDS.items():
            if keyword in content_lower:
                risk_flags.append(flag)

        # 检查高管变动
        if '5.02' in items or '4.01' in items:
            # 进一步检查是否为负面变动
            for keyword in EXECUTIVE_KEYWORDS:
                if keyword.lower() in content_lower:
                    if 'executive_departure' not in risk_flags:
                        risk_flags.append('executive_departure')
                    break

        # 去重
        return list(set(risk_flags))


__all__ = ['SECEventRules']
