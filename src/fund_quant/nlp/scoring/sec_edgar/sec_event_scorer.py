"""
SEC 事件评分器
结合SEC规则pre_score和AI抽取结果计算最终评分
"""
from typing import Dict, Any, Optional


def calculate_sec_event_score(filing: Dict[str, Any], ai_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算SEC事件最终评分

    Args:
        filing: Filing数据（包含pre_score等）
        ai_result: AI抽取结果（可选）

    Returns:
        {
            "final_score": 0-100,
            "trade_priority": "S/A/B/C/D",
            "score_reason": "评分理由"
        }
    """
    # 基础分数
    base_score = filing.get('pre_score', 50)
    adjustments = []

    # 1. 先定义默认值（防止变量未定义）
    event_type = ""
    event_level = ""
    risk_flags = []
    confidence = 0.5

    # 2. 从AI结果提取
    if ai_result:
        event_type = ai_result.get('event_type', '')
        event_level = ai_result.get('event_level', '')
        risk_flags = ai_result.get('risk_flags', [])
        confidence = ai_result.get('confidence', 0.5)

    # 3. 基于AI结果调整分数
    if ai_result and event_type:
        # 事件类型加分
        if event_type == 'earnings_release':
            base_score += 5
            adjustments.append('财报披露+5')

        elif event_type == 'guidance_update':
            base_score += 8
            adjustments.append('指引更新+8')

        elif event_type in ['delisting_risk', 'bankruptcy_restructuring']:
            base_score = max(base_score, 90)
            adjustments.append(f'{event_type}保底90分')

        elif event_type == 'mna_completed':
            base_score += 6
            adjustments.append('并购完成+6')

        # 高管变动风险加分
        if event_type == 'executive_change':
            content = filing.get('content', '').lower()

            # 严格区分CEO/CFO/CAO
            has_ceo_risk = any(p in content for p in [
                'chief executive officer', 'ceo resignation', 'ceo departure',
                'ceo retire', 'ceo termination'
            ])

            has_cfo_risk = any(p in content for p in [
                'chief financial officer', 'cfo resignation', 'cfo departure',
                'cfo retire', 'cfo termination'
            ])

            has_cao_risk = any(p in content for p in [
                'chief accounting officer', 'cao resignation', 'cao departure'
            ])

            # 只有CEO/CFO离职才加高风险分
            if has_ceo_risk:
                base_score += 10
                adjustments.append('CEO离职+10')
            elif has_cfo_risk:
                base_score += 10
                adjustments.append('CFO离职+10')
            elif has_cao_risk:
                # CAO正常变动，检查是否有会计问题
                if any(p in content for p in [
                    'accounting issue', 'restatement', 'material weakness',
                    'auditor resignation', 'internal control'
                ]):
                    base_score += 5
                    adjustments.append('CAO变动+会计问题+5')
            else:
                # 普通董事任命扣分
                if any(p in content for p in [
                    'board of directors', 'member of the board', 'director',
                    'audit committee', 'compensation committee'
                ]):
                    base_score -= 12
                    adjustments.append('普通董事任命-12')

        # event_level调整
        if event_level == 'S':
            base_score = max(base_score, 88)
            adjustments.append('S级事件保底88分')
        elif event_level == 'A':
            base_score = max(base_score, 75)
        elif event_level == 'D':
            base_score = min(base_score, 50)

        # 置信度调整
        if confidence >= 0.8:
            base_score += 3
            adjustments.append(f'高置信度({confidence:.2f})+3')
        elif confidence < 0.5:
            base_score -= 5
            adjustments.append(f'低置信度({confidence:.2f})-5')

    else:
        # 没有AI结果，仅使用pre_score
        adjustments.append('仅SEC规则预评分')

    # 4. 限制在0-100
    final_score = max(0, min(100, base_score))

    # 5. 映射trade_priority（带S级限制）
    if final_score >= 90:
        # S级必须是真正强事件
        s_level_events = [
            'earnings_release', 'guidance_update',
            'delisting_risk', 'bankruptcy_restructuring',
            'mna_completed'
        ]

        # 特殊处理executive_change
        if event_type == 'executive_change':
            content = filing.get('content', '').lower()

            # CAO变动最多A
            if any(p in content for p in ['chief accounting officer', 'cao']):
                trade_priority = 'A'
            # 普通董事最多A
            elif any(p in content for p in ['board of directors', 'member of the board', 'director']):
                if not any(p in content for p in ['ceo', 'cfo', 'chief executive', 'chief financial']):
                    trade_priority = 'A'
                else:
                    trade_priority = 'S'
            else:
                trade_priority = 'S'
        elif event_type in s_level_events:
            trade_priority = 'S'
        else:
            trade_priority = 'A'

    elif final_score >= 80:
        trade_priority = 'A'
    elif final_score >= 65:
        trade_priority = 'B'
    elif final_score >= 50:
        trade_priority = 'C'
    else:
        trade_priority = 'D'

    # 6. 构建评分理由
    score_reason = f"基础分{filing.get('pre_score', 50)}"
    if adjustments:
        score_reason += f"，调整：{'; '.join(adjustments)}"
    score_reason += f"，最终{final_score}分"

    return {
        'final_score': final_score,
        'trade_priority': trade_priority,
        'score_reason': score_reason
    }


__all__ = ['calculate_sec_event_score']
