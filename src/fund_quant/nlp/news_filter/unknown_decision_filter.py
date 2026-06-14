"""
Unknown 新闻二次过滤器（优化版）
对 action=unknown 的新闻进行精细化判断，决定是否真的需要 AI 分析
"""
from typing import Any
from fund_quant.nlp.news_filter.filter_models import FilterResult


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# 权威来源
AUTHORITATIVE_SOURCES = [
    "cls", "财联社", "证券时报", "人民财讯", "公司公告", "交易所公告",
    "巨潮资讯", "上交所", "深交所", "北交所", "互动平台"
]

# 强交易信号（单独出现即可触发）
STRONG_TRADE_SIGNALS = [
    "量产", "投产", "投用", "生产基地", "建设基地", "产线", "扩产",
    "供货", "批量供货", "订单", "中标", "大模型", "芯片", "半导体",
    "机器人", "具身智能", "光模块", "CPO", "卫星", "商业航天",
    "低空经济", "储能", "电池", "创新药", "医疗器械", "靶材",
    "先进制程", "HBM", "算力", "涨价", "提价"
]

# 弱交易信号（需要组合判断）
WEAK_TRADE_SIGNALS = [
    "公司", "股份", "电子", "科技", "集团", "合作", "政策",
    "发布", "推出", "项目", "AI"
]

# 噪音或上下文词（出现时降低交易相关性）
NOISE_OR_CONTEXT_WORDS = [
    "天气", "降雨", "大风", "冰雹", "葬礼", "下葬", "绝不信任",
    "议员", "大使", "外交", "会见", "讲话", "期待未来", "核污染",
    "排海", "异常警报", "投资者数量", "已超", "泛政策"
]

# 地缘政治关键词（普通外交类）
GEOPOLITICAL_KEYWORDS = [
    "外交", "会见", "谅解备忘录", "联合声明", "战略对话",
    "袭击", "冲突", "战争表态", "制裁表态"
]

# 地缘政治市场信号（强相关商品/能源/航运）
GEOPOLITICAL_MARKET_SIGNALS = [
    "霍尔木兹海峡", "油轮", "原油", "商船", "航道", "封锁", "通行受限",
    "断供", "OPEC", "能源运输", "LNG", "天然气供给", "石油禁运",
    "管道", "原油供给", "原油价格", "油价", "能源危机"
]

# 增强信号（配合弱信号使用）
ENHANCEMENT_SIGNALS = [
    "亿元", "万元", "订单", "供货", "客户", "产能", "产品",
    "合同", "项目", "营收", "利润", "业绩"
]


class UnknownDecisionFilter:
    """
    Unknown 新闻二次决策过滤器（优化版）

    职责：
    1. 对 action=unknown 的新闻进行二次判断
    2. 降低低价值新闻进入 AI 的比例
    3. 使用强/弱信号组合判断，避免单个通用词触发
    """

    def __init__(self, symbol_map: dict = None):
        """初始化过滤器"""
        self.authoritative_sources = set(AUTHORITATIVE_SOURCES)
        self.strong_signals = set(STRONG_TRADE_SIGNALS)
        self.weak_signals = set(WEAK_TRADE_SIGNALS)
        self.noise_words = set(NOISE_OR_CONTEXT_WORDS)
        self.geopolitical_kws = set(GEOPOLITICAL_KEYWORDS)
        self.geopolitical_market_signals = set(GEOPOLITICAL_MARKET_SIGNALS)
        self.enhancement_signals = set(ENHANCEMENT_SIGNALS)

        # 内置股票映射表（用于判断是否提及上市公司）
        self.symbol_map = symbol_map or {
            "生益科技": "600183.SH",
            "沪电股份": "002463.SZ",
            "胜宏科技": "300476.SZ",
            "工业富联": "601138.SH",
            "中际旭创": "300308.SZ",
            "新易盛": "300502.SZ",
            "寒武纪": "688256.SH",
            "中芯国际": "688981.SH",
            "中兴通讯": "000063.SZ",
            "江丰电子": "300666.SZ",
            "包钢股份": "600010.SH",
            "中国人保": "601319.SH",
            "京东健康": "06618.HK",
            "小米集团": "01810.HK"
        }

    def _match_keywords(self, text: str, keywords: set) -> list[str]:
        """匹配关键词"""
        text_lower = text.lower()
        matched = []
        for kw in keywords:
            if kw.lower() in text_lower:
                matched.append(kw)
        return matched

    def _contains_listed_company(self, text: str) -> bool:
        """检查文本是否包含上市公司名"""
        for company_name in self.symbol_map.keys():
            if company_name in text:
                return True
        return False

    def refine(self, news: Any, filter_result: Any) -> FilterResult:
        """
        对 unknown 新闻进行二次判断

        Args:
            news: 新闻对象
            filter_result: 过滤结果

        Returns:
            精细化后的 FilterResult
        """
        # 获取当前 action
        action = get_field(filter_result, 'action', '')

        # 如果不是 unknown，直接返回原结果
        if action != "unknown":
            return filter_result

        # 获取新闻字段
        news_id = get_field(news, 'news_id', '')
        source = get_field(news, 'source', '')
        title = get_field(news, 'title', '')
        content = get_field(news, 'content', '')

        # 获取原有字段
        need_ai = get_field(filter_result, 'need_ai', False)
        pre_score = get_field(filter_result, 'pre_score', 30)
        matched_keywords = get_field(filter_result, 'matched_keywords', []).copy()
        matched_rules = get_field(filter_result, 'matched_rules', []).copy()
        reasons = get_field(filter_result, 'reasons', []).copy()
        risk_flags = get_field(filter_result, 'risk_flags', []).copy()

        # 合并标题和内容
        text = f"{title} {content}"

        # 1. 标题和正文都为空
        if (not title or not title.strip()) and (not content or len(content.strip()) < 20):
            return FilterResult(
                news_id=news_id,
                action="archive",
                need_ai=False,
                pre_score=0,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules + ["empty_title_and_content"],
                reasons=reasons + ["标题和正文为空，归档"],
                risk_flags=risk_flags
            )

        # 检查各类关键词
        strong_matches = self._match_keywords(text, self.strong_signals)
        weak_matches = self._match_keywords(text, self.weak_signals)
        noise_matches = self._match_keywords(text, self.noise_words)
        geopolitical_matches = self._match_keywords(text, self.geopolitical_kws)
        geopolitical_market_matches = self._match_keywords(text, self.geopolitical_market_signals)
        enhancement_matches = self._match_keywords(text, self.enhancement_signals)

        # 判断来源
        is_authoritative = source in self.authoritative_sources or any(
            auth_src in source for auth_src in self.authoritative_sources
        )
        is_company_announcement = source in ["公司公告", "交易所公告", "互动平台"]

        # 判断是否提及上市公司
        has_listed_company = self._contains_listed_company(text)

        # 2. 命中噪音词且无强信号 → 过滤
        if noise_matches and not strong_matches:
            matched_keywords.extend(noise_matches)
            matched_rules.append("noise_without_strong_signal")
            reasons.append(f"命中噪音词（{', '.join(noise_matches[:3])}），无强交易信号，暂不进入AI")

            return FilterResult(
                news_id=news_id,
                action="unknown",
                need_ai=False,
                pre_score=15,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 3. 命中地缘政治关键词
        if geopolitical_matches:
            # 如果同时有市场信号（原油/航运/能源），则进入AI
            if geopolitical_market_matches or strong_matches:
                matched_keywords.extend(geopolitical_matches)
                matched_keywords.extend(geopolitical_market_matches)
                matched_rules.append("geopolitical_supply_risk")
                reasons.append(f"地缘政治+市场信号（{', '.join(geopolitical_market_matches[:3])}），进入AI分析")

                return FilterResult(
                    news_id=news_id,
                    action="unknown",
                    need_ai=True,
                    pre_score=max(pre_score, 65),
                    matched_keywords=matched_keywords,
                    matched_rules=matched_rules,
                    reasons=reasons,
                    risk_flags=risk_flags + ["geopolitical_risk"]
                )
            else:
                # 普通地缘政治，无市场信号 → 过滤
                matched_keywords.extend(geopolitical_matches)
                matched_rules.append("geopolitics_without_market_signal")
                reasons.append(f"普通地缘政治新闻（{', '.join(geopolitical_matches[:3])}），无市场信号，暂不进入AI")

                return FilterResult(
                    news_id=news_id,
                    action="unknown",
                    need_ai=False,
                    pre_score=20,
                    matched_keywords=matched_keywords,
                    matched_rules=matched_rules,
                    reasons=reasons,
                    risk_flags=risk_flags
                )

        # 4. 命中强信号 → 进入AI
        if strong_matches:
            matched_keywords.extend(strong_matches)
            matched_rules.append("strong_trade_signal")
            reasons.append(f"命中强交易信号（{', '.join(strong_matches[:5])}），进入AI分析")

            return FilterResult(
                news_id=news_id,
                action="unknown",
                need_ai=True,
                pre_score=max(pre_score, 60),
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 5. 只有弱信号，需要组合判断
        if weak_matches:
            # 条件a：提及上市公司
            if has_listed_company:
                matched_keywords.extend(weak_matches)
                matched_rules.append("weak_signal_with_listed_company")
                reasons.append(f"命中弱信号+上市公司提及，进入AI分析")

                return FilterResult(
                    news_id=news_id,
                    action="unknown",
                    need_ai=True,
                    pre_score=max(pre_score, 50),
                    matched_keywords=matched_keywords,
                    matched_rules=matched_rules,
                    reasons=reasons,
                    risk_flags=risk_flags
                )

            # 条件b：至少两个弱信号，且有增强信号
            if len(set(weak_matches)) >= 2 and enhancement_matches:
                matched_keywords.extend(weak_matches)
                matched_rules.append("multiple_weak_signals_with_enhancement")
                reasons.append(f"命中多个弱信号+增强信号（{', '.join(enhancement_matches[:3])}），进入AI分析")

                return FilterResult(
                    news_id=news_id,
                    action="unknown",
                    need_ai=True,
                    pre_score=max(pre_score, 45),
                    matched_keywords=matched_keywords,
                    matched_rules=matched_rules,
                    reasons=reasons,
                    risk_flags=risk_flags
                )

            # 条件c：来源是公司公告
            if is_company_announcement:
                matched_keywords.extend(weak_matches)
                matched_rules.append("weak_signal_company_announcement")
                reasons.append(f"公司公告来源，进入AI分析")

                return FilterResult(
                    news_id=news_id,
                    action="unknown",
                    need_ai=True,
                    pre_score=max(pre_score, 55),
                    matched_keywords=matched_keywords,
                    matched_rules=matched_rules,
                    reasons=reasons,
                    risk_flags=risk_flags
                )

            # 只有弱信号，不满足条件 → 不进AI
            matched_rules.append("weak_signal_only")
            reasons.append(f"仅命中弱信号（{', '.join(weak_matches[:3])}），无增强条件，暂不进入AI")

            return FilterResult(
                news_id=news_id,
                action="unknown",
                need_ai=False,
                pre_score=25,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 6. 来源权威但无信号 → 不进AI
        if is_authoritative:
            matched_rules.append("authoritative_without_signal")
            reasons.append("来源权威但缺少交易信号，暂不进入AI")

            return FilterResult(
                news_id=news_id,
                action="unknown",
                need_ai=False,
                pre_score=30,
                matched_keywords=matched_keywords,
                matched_rules=matched_rules,
                reasons=reasons,
                risk_flags=risk_flags
            )

        # 7. 其他情况 → 不进AI
        matched_rules.append("no_trade_signal")
        reasons.append("未命中交易信号，暂不进入AI")

        return FilterResult(
            news_id=news_id,
            action="unknown",
            need_ai=False,
            pre_score=20,
            matched_keywords=matched_keywords,
            matched_rules=matched_rules,
            reasons=reasons,
            risk_flags=risk_flags
        )


__all__ = ['UnknownDecisionFilter']
