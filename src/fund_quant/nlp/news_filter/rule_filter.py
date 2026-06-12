"""
简单规则过滤器
"""
from typing import Set

from fund_quant.nlp.news_filter.filter_models import NewsItem, FilterResult
from fund_quant.nlp.news_filter.keyword_rules import (
    RISK_KEYWORDS,
    STRONG_EVENT_KEYWORDS,
    CANDIDATE_KEYWORDS,
    STRONG_ENTITY_KEYWORDS,
    LOW_VALUE_KEYWORDS,
    JUNK_KEYWORDS,
    MACRO_FINANCE_KEYWORDS,
    OVERSEAS_MARKET_KEYWORDS,
    GEOPOLITICS_KEYWORDS,
    MARKET_DATA_KEYWORDS,
    EXEC_NORMAL_CHANGE_KEYWORDS,
    SOCIAL_GOVERNANCE_KEYWORDS,
    AUTHORITATIVE_SOURCES
)


class SimpleRuleFilter:
    """
    简单规则过滤器

    职责：
    1. 规则负责兜底
    2. AI负责理解
    3. 数据库负责留痕
    4. 行情负责验证

    优先级（从高到低）：
    risk > strong_event > candidate > strong_entity > junk > low_value > unknown
    """

    def __init__(self):
        """初始化过滤器"""
        # 将关键词列表转为集合，提高查找效率
        self.risk_kws = set(RISK_KEYWORDS)
        self.strong_event_kws = set(STRONG_EVENT_KEYWORDS)
        self.candidate_kws = set(CANDIDATE_KEYWORDS)
        self.strong_entity_kws = set(STRONG_ENTITY_KEYWORDS)
        self.low_value_kws = set(LOW_VALUE_KEYWORDS)
        self.junk_kws = set(JUNK_KEYWORDS)
        self.macro_finance_kws = set(MACRO_FINANCE_KEYWORDS)
        self.overseas_market_kws = set(OVERSEAS_MARKET_KEYWORDS)
        self.geopolitics_kws = set(GEOPOLITICS_KEYWORDS)
        self.market_data_kws = set(MARKET_DATA_KEYWORDS)
        self.exec_normal_change_kws = set(EXEC_NORMAL_CHANGE_KEYWORDS)
        self.social_governance_kws = set(SOCIAL_GOVERNANCE_KEYWORDS)
        self.authoritative_sources = set(AUTHORITATIVE_SOURCES)

    def filter(self, news: NewsItem) -> FilterResult:
        """
        过滤单条新闻

        Args:
            news: 新闻条目

        Returns:
            过滤结果
        """
        # 检查标题是否为空
        if not news.title or not news.title.strip():
            # 如果 content 也很短，直接归档
            if not news.content or len(news.content.strip()) < 20:
                return FilterResult(
                    news_id=news.news_id,
                    action="archive",
                    need_ai=False,
                    pre_score=5,
                    matched_keywords=[],
                    matched_rules=["empty_title_and_short_content"],
                    reasons=["标题为空且内容过短，直接归档"],
                    risk_flags=[]
                )

        # 合并标题和内容进行匹配
        text = f"{news.title} {news.content}"

        # 记录所有匹配的关键词和规则
        matched_keywords: list[str] = []
        matched_rules: list[str] = []
        reasons: list[str] = []
        risk_flags: list[str] = []

        # 1. 检查社会治理/交通安全关键词（直接归档）
        social_governance_matches = self._match_keywords(text, self.social_governance_kws)
        if social_governance_matches:
            matched_keywords.extend(social_governance_matches)
            matched_rules.append("social_governance_keywords")
            reasons.append(f"命中社会治理/交通安全关键词: {', '.join(social_governance_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="archive",
                need_ai=False,
                pre_score=5,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 2. 检查龙虎榜/市场数据关键词（无交易价值）
        market_data_matches = self._match_keywords(text, self.market_data_kws)
        if market_data_matches:
            matched_keywords.extend(market_data_matches)
            matched_rules.append("market_data_keywords")
            reasons.append(f"命中龙虎榜/市场数据关键词: {', '.join(market_data_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="low_value",
                need_ai=False,
                pre_score=10,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 3. 检查高管普通变动关键词（排除异常情况）
        exec_change_matches = self._match_keywords(text, self.exec_normal_change_kws)
        if exec_change_matches:
            # 检查是否包含异常情况关键词
            abnormal_keywords = ["被调查", "辞职", "失联", "失踪", "被罢免", "被免职", "控制权变更", "实控人变更", "重大资产重组"]
            has_abnormal = any(kw in text for kw in abnormal_keywords)

            if not has_abnormal:
                matched_keywords.extend(exec_change_matches)
                matched_rules.append("exec_normal_change_keywords")
                reasons.append(f"命中高管普通变动关键词: {', '.join(exec_change_matches)}")

                return FilterResult(
                    news_id=news.news_id,
                    action="low_value",
                    need_ai=False,
                    pre_score=20,
                    matched_keywords=matched_keywords,
                    matched_rules=matched_rules,
                    reasons=reasons,
                    risk_flags=risk_flags
                )

        # 4. 检查宏观金融关键词（排除非 A 股标的）
        macro_finance_matches = self._match_keywords(text, self.macro_finance_kws)
        if macro_finance_matches:
            matched_keywords.extend(macro_finance_matches)
            matched_rules.append("macro_finance_keywords")
            reasons.append(f"命中宏观金融关键词: {', '.join(macro_finance_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="low_value",
                need_ai=False,
                pre_score=20,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 5. 检查地缘政治关键词
        geopolitics_matches = self._match_keywords(text, self.geopolitics_kws)
        if geopolitics_matches:
            matched_keywords.extend(geopolitics_matches)
            matched_rules.append("geopolitics_keywords")
            reasons.append(f"命中地缘政治关键词: {', '.join(geopolitics_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="low_value",
                need_ai=False,
                pre_score=15,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 6. 检查海外市场关键词
        overseas_market_matches = self._match_keywords(text, self.overseas_market_kws)
        if overseas_market_matches:
            matched_keywords.extend(overseas_market_matches)
            matched_rules.append("overseas_market_keywords")
            reasons.append(f"命中海外市场关键词: {', '.join(overseas_market_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="low_value",
                need_ai=False,
                pre_score=25,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 7. 检查风险关键词（最高优先级）
        risk_matches = self._match_keywords(text, self.risk_kws)
        if risk_matches:
            matched_keywords.extend(risk_matches)
            matched_rules.append("risk_keywords")
            risk_flags.extend(risk_matches)
            reasons.append(f"命中风险关键词: {', '.join(risk_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="risk",
                need_ai=True,
                pre_score=90,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 8. 检查强事件关键词
        strong_event_matches = self._match_keywords(text, self.strong_event_kws)
        if strong_event_matches:
            matched_keywords.extend(strong_event_matches)
            matched_rules.append("strong_event_keywords")
            reasons.append(f"命中高价值催化关键词: {', '.join(strong_event_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="analyze",
                need_ai=True,
                pre_score=85,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 9. 检查候选关键词
        candidate_matches = self._match_keywords(text, self.candidate_kws)
        if candidate_matches:
            matched_keywords.extend(candidate_matches)
            matched_rules.append("candidate_keywords")
            reasons.append(f"命中潜在题材关键词: {', '.join(candidate_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="candidate",
                need_ai=True,
                pre_score=65,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 10. 检查强实体关键词
        strong_entity_matches = self._match_keywords(text, self.strong_entity_kws)
        if strong_entity_matches:
            matched_keywords.extend(strong_entity_matches)
            matched_rules.append("strong_entity_keywords")
            reasons.append(f"命中强实体关键词: {', '.join(strong_entity_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="candidate",
                need_ai=True,
                pre_score=60,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 11. 检查垃圾关键词
        junk_matches = self._match_keywords(text, self.junk_kws)
        if junk_matches:
            matched_keywords.extend(junk_matches)
            matched_rules.append("junk_keywords")
            reasons.append(f"命中垃圾关键词: {', '.join(junk_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="archive",
                need_ai=False,
                pre_score=5,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 12. 检查低价值关键词
        low_value_matches = self._match_keywords(text, self.low_value_kws)
        if low_value_matches:
            matched_keywords.extend(low_value_matches)
            matched_rules.append("low_value_keywords")
            reasons.append(f"命中低价值财经表达: {', '.join(low_value_matches)}")

            return FilterResult(
                news_id=news.news_id,
                action="low_value",
                need_ai=False,
                pre_score=25,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 13. 未命中任何关键词，根据来源和标题判断
        is_authoritative = news.source in self.authoritative_sources
        has_empty_title = not news.title or not news.title.strip()

        if is_authoritative:
            matched_rules.append("authoritative_source")

            if has_empty_title:
                # 标题为空，降低优先级
                reasons.append("未命中关键词，标题为空，进入AI低优先级分析")
                pre_score = 30
            else:
                reasons.append("未命中关键词，但来源权威，进入AI低优先级分析")
                pre_score = 40

            return FilterResult(
                news_id=news.news_id,
                action="unknown",
                need_ai=True,
                pre_score=pre_score,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )
        else:
            matched_rules.append("unknown_source")
            reasons.append("未命中关键词，普通来源，暂不进AI")

            return FilterResult(
                news_id=news.news_id,
                action="unknown",
                need_ai=False,
                pre_score=30,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

    def _match_keywords(self, text: str, keywords: Set[str]) -> list[str]:
        """
        匹配关键词

        Args:
            text: 待匹配文本
            keywords: 关键词集合

        Returns:
            匹配到的关键词列表
        """
        matches = []
        for keyword in keywords:
            if keyword in text:
                matches.append(keyword)
        return matches


__all__ = ['SimpleRuleFilter']
