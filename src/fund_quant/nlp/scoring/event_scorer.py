"""
事件评分器
根据事件类型、等级、风险标记等计算最终交易优先级分数
"""
from typing import Any


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class EventScorer:
    """
    事件评分器

    职责：
    1. 根据event_level计算基础分
    2. 根据event_type加减分
    3. 根据risk_flags扣分
    4. 根据related_stocks/theme情况调整
    5. 输出final_score和trade_priority
    """

    # 基础分
    LEVEL_BASE_SCORES = {
        'S': 95,
        'A': 85,
        'B': 70,
        'C': 50
    }

    # 事件类型加减分
    EVENT_TYPE_SCORES = {
        'price_increase': 10,
        'order_win': 10,
        'order_growth': 10,
        'mass_production': 8,
        'supply_chain': 8,
        'capacity_build': 5,
        'verification_pass': 8,
        'technical_breakthrough': 12,
        'policy_release': 5,
        'product_release': 0,
        'platform_launch': -10,
        'benchmark_release': -15,
        'dataset_release': -20,
        'research_release': -15,
        'industry_activity': -15,
        'trade_fair_result': -20,
        'business_metric_growth': -15,
        'general': -20
    }

    # 风险扣分
    RISK_PENALTIES = {
        'not_recognized_revenue': -10,
        'rumor_or_unconfirmed': -15,
        'regulatory_risk': -20,
        'litigation_risk': -15,
        'investigation': -20
    }

    def __init__(self):
        """初始化评分器"""
        pass

    def calculate_score(
        self,
        ai_event_result: Any,
        normalized_theme_result: dict = None
    ) -> dict:
        """
        计算最终分数

        Args:
            ai_event_result: AI事件结果对象
            normalized_theme_result: 主题标准化结果

        Returns:
            {
                'final_score': float,
                'trade_priority': str,  # urgent/high/candidate/watch
                'scoring_notes': list[str]
            }
        """
        scoring_notes = []

        # 1. 获取基础分
        event_level = get_field(ai_event_result, 'event_level', 'C')
        base_score = self.LEVEL_BASE_SCORES.get(event_level, 50)
        scoring_notes.append(f"基础分: event_level={event_level} → {base_score}")

        # 2. 事件类型加减分
        event_type = get_field(ai_event_result, 'event_type', 'general')
        type_adjustment = self.EVENT_TYPE_SCORES.get(event_type, 0)
        scoring_notes.append(f"事件类型: {event_type} → {type_adjustment:+d}")

        # 3. 风险扣分
        risk_flags = get_field(ai_event_result, 'risk_flags', [])
        risk_penalty = 0
        for risk_flag in risk_flags:
            penalty = self.RISK_PENALTIES.get(risk_flag, -5)
            risk_penalty += penalty
            scoring_notes.append(f"风险标记: {risk_flag} → {penalty}")

        # 4. 股票和主题情况调整
        related_stocks = get_field(ai_event_result, 'related_stocks', [])
        theme = get_field(ai_event_result, 'theme', '')
        primary_theme_id = None
        if normalized_theme_result:
            primary_theme_id = normalized_theme_result.get('primary_theme_id')

        stock_theme_adjustment = 0

        # 无股票但有主题
        if not related_stocks and (theme or primary_theme_id):
            stock_theme_adjustment = -5
            scoring_notes.append("无股票但有主题 → -5")

            # 如果是高催化事件但无上市公司，额外扣分
            if event_type in ['mass_production', 'capacity_build', 'supply_chain']:
                stock_theme_adjustment -= 5
                scoring_notes.append(f"{event_type}但无上市公司 → 额外-5")

        # 无主题无股票
        if not related_stocks and not theme and not primary_theme_id:
            stock_theme_adjustment = -30
            scoring_notes.append("无主题无股票 → -30")

        # 泛政策/泛会议
        if primary_theme_id == 'general_policy':
            stock_theme_adjustment -= 20
            scoring_notes.append("泛政策/泛会议 → -20")

        # 展会/会议/数据集/平台发布，无上市公司
        if event_type in ['industry_activity', 'trade_fair_result', 'benchmark_release', 'dataset_release', 'platform_launch']:
            if not related_stocks:
                stock_theme_adjustment -= 15
                scoring_notes.append(f"{event_type}且无上市公司 → -15")

        # "全球首个"但无订单/量产/上市公司
        is_market_relevant = get_field(ai_event_result, 'is_market_relevant', True)
        if not is_market_relevant and not related_stocks:
            stock_theme_adjustment -= 10
            scoring_notes.append("不市场相关且无股票 → -10")

        # 特殊规则：展会签约项目（有金额但非公司订单）
        title = get_field(ai_event_result, 'title', '')
        content = get_field(ai_event_result, 'content', '')

        if any(kw in title or kw in content for kw in ["展会", "博览会", "签约", "成交项目"]):
            if any(kw in title or kw in content for kw in ["亿元", "万元"]) and not related_stocks:
                # 展会签约有金额但无具体上市公司
                if event_type == 'general':
                    event_type = 'project_signing'
                    type_adjustment = 0  # 重置为0
                    scoring_notes.append("展会签约项目 → project_signing")
                # 提高基础分到35-40
                if base_score < 40:
                    base_score = 40
                    scoring_notes.append("展会签约保底40分")

        # 特殊规则：调研/政策信号（非订单/业绩）
        if event_type == 'industry_policy_signal' or any(kw in title for kw in ["调研", "考察", "座谈"]):
            if not any(kw in content for kw in ["订单", "合同", "营收", "业绩", "产能"]):
                # 纯调研，保底50分
                if base_score < 50 and base_score > 0:
                    base_score = 50
                    scoring_notes.append("政策调研保底50分")

        # 特殊规则：战略合作框架协议（无金额/订单）
        if "战略合作" in title or "战略协议" in title:
            has_concrete = any(kw in content for kw in ["订单金额", "合同金额", "亿元订单", "万元订单", "采购量"])
            if not has_concrete:
                # 框架协议，降低评分
                if event_type in ['strategic_cooperation', 'material_agreement']:
                    stock_theme_adjustment -= 10
                    scoring_notes.append("战略合作框架协议（无具体金额）→ -10")

        # 5. 计算最终分数
        final_score = base_score + type_adjustment + risk_penalty + stock_theme_adjustment

        # 限制范围 0-100
        final_score = max(0, min(100, final_score))

        # 6. 确定交易优先级
        if final_score >= 85:
            trade_priority = "urgent"
        elif final_score >= 70:
            trade_priority = "high"
        elif final_score >= 55:
            trade_priority = "candidate"
        else:
            trade_priority = "watch"

        # 7. 特殊优先级调整
        # 战略合作框架协议不应high（即使分数达到）
        if "战略合作" in title or "战略协议" in title:
            has_concrete = any(kw in content for kw in ["订单金额", "合同金额", "亿元订单", "万元订单", "采购量"])
            if not has_concrete and trade_priority in ["high", "urgent"]:
                trade_priority = "watch"
                scoring_notes.append("战略合作框架协议降级 → watch")

        # 调研/考察类不应urgent
        if any(kw in title for kw in ["调研", "考察", "座谈", "会见"]):
            if trade_priority == "urgent":
                trade_priority = "high"
                scoring_notes.append("调研类降级 → high")

        scoring_notes.append(f"最终分数: {final_score:.1f}, 优先级: {trade_priority}")

        return {
            'final_score': final_score,
            'trade_priority': trade_priority,
            'scoring_notes': scoring_notes
        }


__all__ = ['EventScorer']
