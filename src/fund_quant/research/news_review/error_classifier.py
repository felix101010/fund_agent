"""
错误标签分类器
自动为处理结果打上错误标签，便于后续人工复盘
"""
from typing import Any, List


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class ErrorClassifier:
    """
    错误标签分类器

    职责：
    根据处理结果自动生成错误标签，用于样本筛选和复盘
    """

    # 上市公司名称列表（用于检测stock_missing）
    LISTED_COMPANY_KEYWORDS = [
        "江丰电子", "包钢股份", "徐工机械", "京东健康", "中兴通讯",
        "生益科技", "沪电股份", "胜宏科技", "工业富联", "中际旭创",
        "新易盛", "寒武纪", "中芯国际", "中国人保", "小米集团"
    ]

    @staticmethod
    def classify(process_result: Any) -> List[str]:
        """
        对处理结果分类，生成错误标签

        Args:
            process_result: NewsProcessResult对象

        Returns:
            错误标签列表
        """
        error_tags = []

        # 获取字段
        used_fallback = get_field(process_result, 'used_fallback', False)
        final_event = get_field(process_result, 'final_event', None)
        validation_errors = get_field(process_result, 'validation_errors', [])
        title = get_field(process_result, 'title', '')
        content = get_field(process_result, 'content', '')

        if not final_event:
            return error_tags

        # 提取事件字段
        final_score = get_field(final_event, 'final_score', 0.0)
        related_stocks = get_field(final_event, 'related_stocks', [])
        primary_theme_id = get_field(final_event, 'primary_theme_id', '')
        primary_theme_name = get_field(final_event, 'primary_theme_name', '')
        is_market_relevant = get_field(final_event, 'is_market_relevant', True)
        related_etfs = get_field(final_event, 'related_etfs', [])
        trade_priority = get_field(final_event, 'trade_priority', 'watch')
        theme_confidence = get_field(final_event, 'theme_confidence', 0.0)
        risk_flags = get_field(final_event, 'risk_flags', [])
        event_type = get_field(final_event, 'event_type', '')

        # 规则1: used_fallback=True
        if used_fallback:
            error_tags.append("fallback_used")

        # 规则2: final_score >= 75 且 related_stocks为空
        if final_score >= 75 and not related_stocks:
            error_tags.append("high_score_without_stock")

        # 规则3: primary_theme_id 为空且 is_market_relevant=True
        if not primary_theme_id and is_market_relevant:
            error_tags.append("theme_missing")

        # 规则4: validation_errors 非空
        if validation_errors:
            error_tags.append("validation_error")

        # 规则5: related_stocks 被 Validator 删除
        if any("删除" in str(e) or "delete" in str(e).lower() for e in validation_errors):
            error_tags.append("stock_invalid_deleted")

        # 规则6: risk关键词命中但 risk_flags 为空
        risk_keywords = ["未形成收入", "尚未形成收入", "传闻", "网传", "澄清", "不涉及"]
        text = f"{title} {content}".lower()
        has_risk_keyword = any(kw in text for kw in risk_keywords)
        if has_risk_keyword and not risk_flags:
            error_tags.append("risk_flag_missing")

        # 规则7: related_etfs 非空但 primary_theme_id 置信度低
        if related_etfs and theme_confidence < 0.6:
            error_tags.append("etf_suspicious")

        # 规则8: title 包含"光波导"但 primary_theme_id=new_energy_vehicle
        if "光波导" in title and primary_theme_id == "new_energy_vehicle":
            error_tags.append("theme_suspicious")

        # 规则9: title 包含"上交会/展会/意向成交"但 related_etfs 非空
        fair_keywords = ["上交会", "展会", "博览会", "意向成交", "成交项目数"]
        if any(kw in title for kw in fair_keywords) and related_etfs:
            error_tags.append("etf_suspicious")

        # 规则10: title 包含上市公司名称但 related_stocks 为空
        has_company_name = any(company in title for company in ErrorClassifier.LISTED_COMPANY_KEYWORDS)
        if has_company_name and not related_stocks:
            error_tags.append("stock_missing")

        # 规则11: trade_priority=urgent 但没有明确催化
        if trade_priority == "urgent":
            has_strong_catalyst = any(kw in text for kw in ["订单金额", "亿元", "量产", "涨价", "中标", "供货"])
            if not related_stocks and not has_strong_catalyst:
                error_tags.append("priority_suspicious")

        # 规则12: 变压器映射AI算力
        if "变压器" in title and primary_theme_id == "ai_compute":
            error_tags.append("theme_suspicious")

        return error_tags


__all__ = ['ErrorClassifier']
