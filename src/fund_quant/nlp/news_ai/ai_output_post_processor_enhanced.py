"""
AI 输出后处理器 - 增强版
将不稳定的 AI 原始输出转换为稳定的结构化结果，并清洗 related_stocks
集成主题标准化、市场映射、事件评分、风险标记提取
"""
import re
from typing import Any
from fund_quant.nlp.entity_linking.stock_entity_resolver import StockEntityResolver
from fund_quant.nlp.theme_mapping.theme_normalizer import ThemeNormalizer
from fund_quant.nlp.theme_mapping.market_mapping_enricher import MarketMappingEnricher
from fund_quant.nlp.scoring.event_scorer import EventScorer
from fund_quant.nlp.news_filter.keyword_rules import RISK_KEYWORD_TO_FLAG


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class AIOutputPostProcessor:
    """
    AI 输出后处理器（增强版）

    新增职责：
    1. 调用 StockEntityResolver 清洗 related_stocks
    2. 事件类型标准化（批量供货、量产、投产等）
    3. 主题补全（靶材→半导体材料，光模块→光模块/CPO等）
    4. novelty_type 保守修正（限制 new_theme 判断）
    5. 市场相关性修正
    6. 记录所有修正到 postprocess_notes
    """

    # 新增：主题补全映射（产业关键词→产业主题）
    THEME_COMPLETION_MAP = {
        "半导体材料": ["靶材", "先进制程", "存储芯片"],
        "光模块/CPO": ["光模块", "CPO", "800G", "1.6T"],
        "机器人": ["机器人", "具身智能", "NeuroVLA", "灵巧手"],
        "AI算力": ["算力", "数据中心"],
        "AI医疗": ["医院", "专科", "医疗", "健康"],
        "AI工业应用": ["炼钢", "工业", "智能制造"],
        "卫星产业": ["卫星", "商业航天", "SpaceX", "低轨卫星"]
    }

    # 公司名列表（需要从theme中移除）
    COMPANY_NAMES = {
        "生益科技", "沪电股份", "胜宏科技", "工业富联", "中际旭创", "新易盛",
        "寒武纪", "中芯国际", "中兴通讯", "江丰电子", "包钢股份", "中国人保",
        "京东健康", "小米集团"
    }

    # 新增：强催化词（允许 new_theme）
    STRONG_CATALYST_KEYWORDS = [
        "全球首个", "国内首个", "首个", "新材料", "新工艺", "新技术",
        "新产品", "新平台", "新模型", "新路线", "突破", "发布", "推出"
    ]

    # 新增：低价值噪音词（不允许 new_theme）
    LOW_VALUE_NOISE_KEYWORDS = [
        "天气", "葬礼", "外交表态", "人物活动", "访问", "会见", "讲话",
        "倡议", "表示", "期待"
    ]

    def __init__(self):
        """初始化后处理器"""
        self.stock_resolver = StockEntityResolver()
        self.theme_normalizer = ThemeNormalizer()
        self.market_enricher = MarketMappingEnricher(self.theme_normalizer)
        self.event_scorer = EventScorer()

    def process(self, news: Any, filter_result: Any, ai_event_result: Any) -> Any:
        """
        后处理 AI 事件结果

        Args:
            news: 新闻对象
            filter_result: 过滤结果
            ai_event_result: AI 事件结果

        Returns:
            增强后的 AIEventResult
        """
        postprocess_notes = []

        # 获取文本
        title = get_field(news, 'title', '')
        content = get_field(news, 'content', '')
        text = f"{title} {content}"

        # 获取 matched_keywords
        matched_keywords = get_field(filter_result, 'matched_keywords', [])

        # ===== 0. 保存AI原始主题（在任何修正之前）=====
        original_theme = get_field(ai_event_result, 'theme', '')
        if hasattr(ai_event_result, '__dict__'):
            ai_event_result.raw_themes = original_theme
        else:
            ai_event_result['raw_themes'] = original_theme

        # 0.5. 提取风险标记（从文本中）
        risk_flags = self._extract_risk_flags(text)
        if risk_flags:
            postprocess_notes.extend([f"提取风险标记: {', '.join(risk_flags)}"])

        # 1. 事件类型修正
        original_event_type = get_field(ai_event_result, 'event_type', '')
        event_type, event_type_notes = self._correct_event_type(
            text, matched_keywords, original_event_type
        )
        postprocess_notes.extend(event_type_notes)

        # 2. 事件等级修正
        original_event_level = get_field(ai_event_result, 'event_level', 'C')
        event_level, event_level_notes = self._correct_event_level(
            text, event_type, original_event_level
        )
        postprocess_notes.extend(event_level_notes)

        # 3. 情绪修正
        original_sentiment = get_field(ai_event_result, 'sentiment', 'neutral')
        sentiment, sentiment_notes = self._correct_sentiment(
            text, event_type, original_sentiment
        )
        postprocess_notes.extend(sentiment_notes)

        # 4. 主题补全（增强：支持公司名→产业主题转换）
        original_theme = get_field(ai_event_result, 'theme', '')
        theme, theme_notes = self._complete_theme(text, original_theme)
        postprocess_notes.extend(theme_notes)

        # 5. novelty_type 修正
        original_novelty_type = get_field(ai_event_result, 'novelty_type', 'noise')
        novelty_type, novelty_notes = self._correct_novelty_type(
            text, event_type, original_novelty_type
        )
        postprocess_notes.extend(novelty_notes)

        # 6. 清洗并补充 related_stocks
        # 先从AI输出中清洗
        resolve_result = self.stock_resolver.resolve(ai_event_result)

        # 再从文本中补充（避免重复）
        text_stocks_result = self.stock_resolver.resolve_from_text(
            title, content, resolve_result.related_stocks
        )

        # 合并结果
        resolve_result.related_stocks.extend(text_stocks_result.related_stocks)
        resolve_result.warnings.extend(text_stocks_result.warnings)

        if resolve_result.warnings:
            postprocess_notes.extend([f"stock_resolve: {w}" for w in resolve_result.warnings])

        # 7. 市场相关性修正
        original_is_market_relevant = get_field(ai_event_result, 'is_market_relevant', True)
        is_market_relevant, relevance_notes = self._correct_market_relevance(
            text, event_type, theme, resolve_result.related_stocks, original_is_market_relevant
        )
        postprocess_notes.extend(relevance_notes)

        # 8. 置信度修正
        original_confidence = get_field(ai_event_result, 'confidence', 0.5)
        confidence, confidence_notes = self._correct_confidence(
            resolve_result.related_stocks, theme, event_type, is_market_relevant, original_confidence
        )
        postprocess_notes.extend(confidence_notes)

        # 更新 ai_event_result 字段（基础字段）
        if hasattr(ai_event_result, '__dict__'):
            # dataclass 对象
            ai_event_result.event_type = event_type
            ai_event_result.event_level = event_level
            ai_event_result.sentiment = sentiment
            ai_event_result.theme = theme
            ai_event_result.novelty_type = novelty_type
            ai_event_result.related_stocks = resolve_result.related_stocks
            ai_event_result.related_entities = resolve_result.related_entities
            ai_event_result.is_market_relevant = is_market_relevant
            ai_event_result.confidence = confidence
            ai_event_result.risk_flags = risk_flags  # 更新风险标记
            ai_event_result.postprocess_notes = postprocess_notes
        else:
            # dict 对象
            ai_event_result['event_type'] = event_type
            ai_event_result['event_level'] = event_level
            ai_event_result['sentiment'] = sentiment
            ai_event_result['theme'] = theme
            ai_event_result['novelty_type'] = novelty_type
            ai_event_result['related_stocks'] = resolve_result.related_stocks
            ai_event_result['related_entities'] = resolve_result.related_entities
            ai_event_result['is_market_relevant'] = is_market_relevant
            ai_event_result['confidence'] = confidence
            ai_event_result['risk_flags'] = risk_flags  # 更新风险标记
            ai_event_result['postprocess_notes'] = postprocess_notes

        # ===== 新增：主题标准化、市场映射、事件评分 =====

        # 9. 主题标准化（raw_themes已在步骤0保存）
        try:
            # 需要传递title和content，临时从news获取
            # 将title和content临时附加到ai_event_result供ThemeNormalizer使用
            if hasattr(ai_event_result, '__dict__'):
                ai_event_result.title = title
                ai_event_result.content = content
            else:
                ai_event_result['title'] = title
                ai_event_result['content'] = content

            normalized_theme_result = self.theme_normalizer.normalize(ai_event_result)

            # 更新主题标准化字段
            if hasattr(ai_event_result, '__dict__'):
                ai_event_result.primary_theme_id = normalized_theme_result.get('primary_theme_id', '')
                ai_event_result.primary_theme_name = normalized_theme_result.get('primary_theme_name', '')
                ai_event_result.normalized_themes = normalized_theme_result.get('normalized_themes', [])
                ai_event_result.theme_confidence = normalized_theme_result.get('theme_confidence', 0.0)
                ai_event_result.mapping_notes = normalized_theme_result.get('mapping_notes', [])
            else:
                ai_event_result['primary_theme_id'] = normalized_theme_result.get('primary_theme_id', '')
                ai_event_result['primary_theme_name'] = normalized_theme_result.get('primary_theme_name', '')
                ai_event_result['normalized_themes'] = normalized_theme_result.get('normalized_themes', [])
                ai_event_result['theme_confidence'] = normalized_theme_result.get('theme_confidence', 0.0)
                ai_event_result['mapping_notes'] = normalized_theme_result.get('mapping_notes', [])
        except Exception as e:
            postprocess_notes.append(f"主题标准化失败: {str(e)}")
            normalized_theme_result = {
                'primary_theme_id': '',
                'primary_theme_name': '',
                'normalized_themes': [],
                'theme_confidence': 0.0,
                'mapping_notes': []
            }

        # 10. 市场映射增强
        try:
            market_result = self.market_enricher.enrich(ai_event_result, normalized_theme_result)

            if hasattr(ai_event_result, '__dict__'):
                ai_event_result.related_indices = market_result.get('related_indices', [])
                ai_event_result.related_etfs = market_result.get('related_etfs', [])
                ai_event_result.candidate_stock_pool_theme = market_result.get('candidate_stock_pool_theme', '')
                # 合并enrichment_notes到mapping_notes
                ai_event_result.mapping_notes.extend(market_result.get('enrichment_notes', []))
            else:
                ai_event_result['related_indices'] = market_result.get('related_indices', [])
                ai_event_result['related_etfs'] = market_result.get('related_etfs', [])
                ai_event_result['candidate_stock_pool_theme'] = market_result.get('candidate_stock_pool_theme', '')
                ai_event_result['mapping_notes'].extend(market_result.get('enrichment_notes', []))
        except Exception as e:
            postprocess_notes.append(f"市场映射失败: {str(e)}")

        # 11. 事件评分
        try:
            score_result = self.event_scorer.calculate_score(ai_event_result, normalized_theme_result)

            if hasattr(ai_event_result, '__dict__'):
                ai_event_result.final_score = score_result.get('final_score', 0.0)
                ai_event_result.trade_priority = score_result.get('trade_priority', 'watch')
                # 合并scoring_notes到postprocess_notes
                ai_event_result.postprocess_notes.extend(score_result.get('scoring_notes', []))
            else:
                ai_event_result['final_score'] = score_result.get('final_score', 0.0)
                ai_event_result['trade_priority'] = score_result.get('trade_priority', 'watch')
                ai_event_result['postprocess_notes'].extend(score_result.get('scoring_notes', []))
        except Exception as e:
            postprocess_notes.append(f"事件评分失败: {str(e)}")

        return ai_event_result

    def _correct_event_type(
        self, text: str, matched_keywords: list, original_event_type: str
    ) -> tuple[str, list[str]]:
        """事件类型修正"""
        notes = []
        event_type = original_event_type

        text_lower = text.lower()

        # 1. 批量供货/供货/进入供应链
        if any(kw in text_lower for kw in ["批量供货", "供货", "进入供应链"]):
            if event_type != "supply_chain":
                event_type = "supply_chain"
                notes.append("event_type修正为supply_chain（批量供货）")

        # 2. 量产
        elif any(kw in text_lower for kw in ["量产"]):
            if event_type != "mass_production":
                event_type = "mass_production"
                notes.append("event_type修正为mass_production（量产）")

        # 3. 投产/投用/生产基地/建设基地/扩产
        elif any(kw in text_lower for kw in ["投产", "投用", "生产基地", "建设基地", "扩产"]):
            if event_type != "capacity_build":
                event_type = "capacity_build"
                notes.append("event_type修正为capacity_build（产能建设）")

        # 4. 发布/推出/全球首个/首个
        elif any(kw in text_lower for kw in ["发布", "推出", "全球首个", "首个"]):
            if event_type == "general":
                event_type = "product_release"
                notes.append("event_type修正为product_release（产品发布）")

        # 5. 澄清/暂无相关业务/不涉及/未量产/未形成收入
        elif any(kw in text_lower for kw in ["澄清", "暂无相关业务", "不涉及", "未量产", "未形成收入"]):
            if event_type != "risk_disconfirm":
                event_type = "risk_disconfirm"
                notes.append("event_type修正为risk_disconfirm（风险澄清）")

        # 6. 审查调查/纪律审查/监察调查/严重违纪违法
        elif any(kw in text_lower for kw in ["审查调查", "纪律审查", "监察调查", "严重违纪违法"]):
            if event_type != "regulatory_investigation":
                event_type = "regulatory_investigation"
                notes.append("event_type修正为regulatory_investigation（监管调查）")

        # 7. 涨价/提价
        elif any(kw in text_lower for kw in ["涨价", "提价"]):
            if event_type != "price_increase":
                event_type = "price_increase"
                notes.append("event_type修正为price_increase（涨价）")

        return event_type, notes

    def _correct_event_level(
        self, text: str, event_type: str, original_event_level: str
    ) -> tuple[str, list[str]]:
        """事件等级修正"""
        notes = []
        event_level = original_event_level

        text_lower = text.lower()

        # 批量供货/量产 → 至少 A
        if event_type in ["supply_chain", "mass_production"]:
            if event_level not in ["S", "A"]:
                event_level = "A"
                notes.append(f"event_level提升为A（{event_type}）")

        # 涨价 → 至少 A
        elif event_type == "price_increase":
            if event_level not in ["S", "A"]:
                event_level = "A"
                notes.append("event_level提升为A（涨价）")

        # 产能建设 → 至少 B
        elif event_type == "capacity_build":
            if event_level == "C":
                event_level = "B"
                notes.append("event_level提升为B（产能建设）")

        # 产品发布 → 至少 B，全球首个 → 至少 A
        elif event_type == "product_release":
            if "全球首个" in text_lower:
                if event_level not in ["S", "A"]:
                    event_level = "A"
                    notes.append("event_level提升为A（全球首个）")
            elif event_level == "C":
                event_level = "B"
                notes.append("event_level提升为B（产品发布）")

        # 监管调查 → 保持原等级，不强制修改

        return event_level, notes

    def _correct_sentiment(
        self, text: str, event_type: str, original_sentiment: str
    ) -> tuple[str, list[str]]:
        """情绪修正"""
        notes = []
        sentiment = original_sentiment

        text_lower = text.lower()

        # 批量供货/量产/产能建设/涨价 → positive
        if event_type in ["supply_chain", "mass_production", "capacity_build", "price_increase"]:
            if sentiment != "positive":
                sentiment = "positive"
                notes.append(f"sentiment修正为positive（{event_type}）")

        # 产品发布 → positive 或 neutral
        elif event_type == "product_release":
            if sentiment == "negative":
                sentiment = "neutral"
                notes.append("sentiment修正为neutral（产品发布）")

        # 风险澄清/监管调查 → negative
        elif event_type in ["risk_disconfirm", "regulatory_investigation"]:
            if sentiment != "negative":
                sentiment = "negative"
                notes.append(f"sentiment修正为negative（{event_type}）")

        return sentiment, notes

    def _complete_theme(self, text: str, original_theme: str) -> tuple[str, list[str]]:
        """主题补全（增强：支持公司名→产业主题转换）"""
        notes = []
        theme = original_theme

        text_lower = text.lower()

        # 1. 如果theme是公司名，尝试替换为产业主题
        if theme in self.COMPANY_NAMES:
            # 扫描文本，匹配产业关键词
            matched_industry_theme = None
            for industry_theme, keywords in self.THEME_COMPLETION_MAP.items():
                if any(kw in text_lower for kw in keywords):
                    matched_industry_theme = industry_theme
                    break

            if matched_industry_theme:
                notes.append(f"postprocess: theme company_name({theme}) -> {matched_industry_theme}")
                theme = matched_industry_theme
            else:
                # 没有匹配到产业主题，保留但标记
                notes.append(f"postprocess: theme保留公司名{theme}（未匹配到产业关键词）")

        # 2. 如果主题为空或"无"，尝试补全
        elif not theme or theme == "无":
            for theme_name, keywords in self.THEME_COMPLETION_MAP.items():
                if any(kw in text_lower for kw in keywords):
                    theme = theme_name
                    notes.append(f"theme补全为{theme_name}（命中关键词）")
                    break

        # 3. 特殊处理：同时包含大模型和AI
        if "大模型" in text_lower or "ai" in text_lower:
            if "医院" in text_lower or "医疗" in text_lower or "专科" in text_lower or "健康" in text_lower:
                if theme != "AI医疗":
                    theme = "AI医疗"
                    notes.append(f"theme修正为AI医疗（大模型+医疗场景）")
            elif "炼钢" in text_lower or "工业" in text_lower or "制造" in text_lower:
                if theme != "AI工业应用":
                    theme = "AI工业应用"
                    notes.append(f"theme修正为AI工业应用（AI+工业场景）")

        return theme, notes

    def _correct_novelty_type(
        self, text: str, event_type: str, original_novelty_type: str
    ) -> tuple[str, list[str]]:
        """novelty_type 保守修正"""
        notes = []
        novelty_type = original_novelty_type

        text_lower = text.lower()

        # 如果是 new_theme，检查是否合理
        if novelty_type == "new_theme":
            # 1. event_type 是 general 且没有强催化词 → 降级
            if event_type == "general":
                has_catalyst = any(kw in text_lower for kw in self.STRONG_CATALYST_KEYWORDS)
                if not has_catalyst:
                    novelty_type = "noise"
                    notes.append("novelty_type降级为noise（general事件无强催化）")

            # 2. 命中低价值噪音词 → 降级
            has_noise = any(kw in text_lower for kw in self.LOW_VALUE_NOISE_KEYWORDS)
            if has_noise:
                has_catalyst = any(kw in text_lower for kw in self.STRONG_CATALYST_KEYWORDS)
                if not has_catalyst:
                    novelty_type = "noise"
                    notes.append("novelty_type降级为noise（命中低价值噪音词）")

        # 风险澄清/监管调查 → negative_disconfirm
        if event_type in ["risk_disconfirm", "regulatory_investigation"]:
            if novelty_type != "negative_disconfirm":
                novelty_type = "negative_disconfirm"
                notes.append(f"novelty_type修正为negative_disconfirm（{event_type}）")

        # 批量供货/量产/产能建设 → old_theme_new_progress
        elif event_type in ["supply_chain", "mass_production", "capacity_build"]:
            if novelty_type not in ["new_theme", "negative_disconfirm"]:
                novelty_type = "old_theme_new_progress"
                notes.append(f"novelty_type修正为old_theme_new_progress（{event_type}）")

        return novelty_type, notes

    def _correct_market_relevance(
        self, text: str, event_type: str, theme: str,
        related_stocks: list, original_is_market_relevant: bool
    ) -> tuple[bool, list[str]]:
        """市场相关性修正"""
        notes = []
        is_market_relevant = original_is_market_relevant

        text_lower = text.lower()

        # 1. 没有股票、没有主题、event_type 是 general → 不相关
        if not related_stocks and (not theme or theme == "无") and event_type == "general":
            if is_market_relevant:
                is_market_relevant = False
                notes.append("is_market_relevant修正为False（无股票、无主题、通用事件）")

        # 2. 命中低价值噪音词，且没有股票和主题 → 不相关
        has_noise = any(kw in text_lower for kw in self.LOW_VALUE_NOISE_KEYWORDS)
        if has_noise and not related_stocks and (not theme or theme == "无"):
            if is_market_relevant:
                is_market_relevant = False
                notes.append("is_market_relevant修正为False（低价值噪音且无股票主题）")

        # 3. 有强事件但无股票 → 保持相关，但后续会降低置信度

        return is_market_relevant, notes

    def _correct_confidence(
        self, related_stocks: list, theme: str, event_type: str,
        is_market_relevant: bool, original_confidence: float
    ) -> tuple[float, list[str]]:
        """置信度修正"""
        notes = []
        confidence = original_confidence

        # 1. 不市场相关 → 不超过 0.4
        if not is_market_relevant:
            if confidence > 0.4:
                confidence = 0.4
                notes.append("confidence降低为0.4（不市场相关）")

        # 2. 没有股票，没有主题，general 事件 → 不超过 0.4
        elif not related_stocks and (not theme or theme == "无") and event_type == "general":
            if confidence > 0.4:
                confidence = 0.4
                notes.append("confidence降低为0.4（无股票、无主题、通用事件）")

        # 3. 没有股票，但有明确主题和强事件 → 不超过 0.75
        elif not related_stocks and theme and theme != "无":
            if event_type in ["product_release", "capacity_build", "supply_chain", "mass_production"]:
                if confidence > 0.75:
                    confidence = 0.75
                    notes.append("confidence限制为0.75（有主题强事件但无股票）")

        return confidence, notes

    def _extract_risk_flags(self, text: str) -> list[str]:
        """从文本中提取风险标记"""
        risk_flags = []
        text_lower = text.lower()

        for keyword, flag in RISK_KEYWORD_TO_FLAG.items():
            if keyword in text_lower:
                if flag not in risk_flags:
                    risk_flags.append(flag)

        return risk_flags


__all__ = ['AIOutputPostProcessor']
