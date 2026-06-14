"""
AI 事件抽取器
"""
import json
from typing import Any, Optional

from fund_quant.nlp.news_ai.ai_event_models import AIEventResult, RelatedStock
from fund_quant.nlp.news_ai.prompt_builder import PromptBuilder, get_field
from fund_quant.nlp.news_ai.ai_result_validator import AIResultValidator
from fund_quant.nlp.news_ai.ai_output_post_processor_enhanced import AIOutputPostProcessor


class AIEventExtractor:
    """AI 事件抽取器"""

    # 股票代码映射（简单版）
    STOCK_MAPPING = {
        "生益科技": "600183.SH",
        "沪电股份": "002463.SZ",
        "胜宏科技": "300476.SZ",
        "工业富联": "601138.SH",
        "中际旭创": "300308.SZ",
        "新易盛": "300502.SZ",
        "寒武纪": "688256.SH",
        "长鑫存储": "",
        "中芯国际": "688981.SH",
        "台积电": "",
        "中兴通讯": "000063.SZ"
    }

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        validator: Optional[AIResultValidator] = None,
        post_processor: Optional[AIOutputPostProcessor] = None
    ):
        """
        初始化抽取器

        Args:
            llm_client: LLM 客户端（需要有 generate(prompt: str) -> str 方法）
            prompt_builder: Prompt 构建器
            validator: 结果验证器
            post_processor: AI 输出后处理器
        """
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.validator = validator or AIResultValidator()
        self.post_processor = post_processor or AIOutputPostProcessor()

    def should_extract(self, filter_result: Any) -> bool:
        """
        判断是否需要进行事件抽取

        Args:
            filter_result: 过滤结果

        Returns:
            是否需要抽取
        """
        need_ai = get_field(filter_result, 'need_ai', False)
        action = get_field(filter_result, 'action', '')

        return need_ai is True and action in {"candidate", "analyze", "risk", "unknown"}

    def extract(self, news: Any, filter_result: Any) -> AIEventResult:
        """
        抽取事件

        Args:
            news: 新闻对象
            filter_result: 过滤结果

        Returns:
            AIEventResult
        """
        news_id = get_field(news, 'news_id', '')

        # 如果不需要抽取，返回空事件
        if not self.should_extract(filter_result):
            return AIEventResult(
                news_id=news_id,
                is_market_relevant=False,
                event_type="general",
                theme="",
                sub_themes=[],
                related_stocks=[],
                sentiment="neutral",
                event_level="C",
                novelty_type="noise",
                summary="",
                confidence=0.0,
                risk_flags=[],
                raw_ai_response="",
                is_valid=True,
                validation_errors=[]
            )

        # 如果没有 LLM 客户端，使用 fallback 规则
        if self.llm_client is None:
            return self._fallback_rule_extract(news, filter_result)

        # 使用 LLM 进行抽取
        try:
            prompt = self.prompt_builder.build(news, filter_result)
            raw_response = self.llm_client.generate(prompt)

            # 验证 AI 原始输出
            result = self.validator.validate(news, filter_result, raw_response)

            # 如果验证失败，使用 fallback
            if not result.is_valid:
                print(f"⚠️  AI 输出验证失败: {result.validation_errors}")
                fallback_result = self._fallback_rule_extract(news, filter_result)
                fallback_result.raw_ai_response = raw_response
                fallback_result.validation_errors.append("AI输出验证失败，已使用fallback结果")
                # fallback 结果也需要后处理
                fallback_result = self.post_processor.process(news, filter_result, fallback_result)
                return fallback_result

            # AI 输出有效，进行后处理
            result = self.post_processor.process(news, filter_result, result)

            return result

        except Exception as e:
            # LLM 调用失败，降级到 fallback
            print(f"❌ AI 调用异常: {e}")
            fallback_result = self._fallback_rule_extract(news, filter_result)
            fallback_result.validation_errors.append(f"AI调用异常，已使用fallback结果: {str(e)}")
            return fallback_result

    def _fallback_rule_extract(self, news: Any, filter_result: Any) -> AIEventResult:
        """
        Fallback 规则抽取（不依赖 LLM）

        Args:
            news: 新闻对象
            filter_result: 过滤结果

        Returns:
            AIEventResult
        """
        news_id = get_field(news, 'news_id', '')
        title = get_field(news, 'title', '')
        content = get_field(news, 'content', '')
        action = get_field(filter_result, 'action', '')

        text = f"{title} {content}"

        # 初始化结果
        event_type = "general"
        sentiment = "neutral"
        event_level = "B"
        novelty_type = "old_theme_new_progress"
        confidence = 0.60

        # 规则1: risk 类型
        if action == "risk":
            event_type = "risk_disconfirm"
            sentiment = "negative"
            event_level = "A"
            novelty_type = "negative_disconfirm"
            confidence = 0.80

        # 规则2: 验证通过/认证通过
        elif "验证通过" in text or "认证通过" in text:
            event_type = "verification_pass"
            sentiment = "positive"
            event_level = "A"
            novelty_type = "old_theme_new_progress"
            confidence = 0.80

        # 规则3: 送样
        elif "送样" in text:
            event_type = "sample_delivery"
            sentiment = "positive"
            event_level = "A"
            novelty_type = "old_theme_new_progress"
            confidence = 0.80

        # 规则4: 量产
        elif "量产" in text:
            event_type = "mass_production"
            sentiment = "positive"
            event_level = "A"
            novelty_type = "old_theme_new_progress"
            confidence = 0.80

        # 规则5: 中标/订单
        elif "中标" in text or "订单" in text:
            event_type = "order_win"
            sentiment = "positive"
            event_level = "A"
            novelty_type = "old_theme_new_progress"
            confidence = 0.80

        # 规则6: 涨价/提价
        elif "涨价" in text or "提价" in text:
            event_type = "price_increase"
            sentiment = "positive"
            event_level = "A"
            novelty_type = "old_theme_new_progress"
            confidence = 0.80

        # 规则7: 战略合作
        elif "战略合作" in text:
            event_type = "strategic_cooperation"
            sentiment = "positive"
            event_level = "B"
            novelty_type = "old_theme_new_progress"
            confidence = 0.70

        # 调整 confidence（根据 action）
        if action == "analyze":
            confidence = max(confidence, 0.80)
        elif action == "candidate":
            confidence = max(confidence, 0.70)
        elif action == "unknown":
            confidence = min(confidence, 0.60)

        # 识别主题
        theme = self._identify_theme(text)

        # 识别关联股票
        related_stocks = self._identify_stocks(text)

        # 生成摘要
        summary = title[:120] if title else ""

        # 构造 fallback 结果的 JSON
        fallback_data = {
            "is_market_relevant": True,
            "event_type": event_type,
            "theme": theme,
            "sub_themes": [],
            "related_stocks": [
                {"code": s.code, "name": s.name, "reason": s.reason}
                for s in related_stocks
            ],
            "sentiment": sentiment,
            "event_level": event_level,
            "novelty_type": novelty_type,
            "summary": summary,
            "confidence": confidence,
            "risk_flags": []
        }

        # 通过 validator 验证（保持路径一致）
        raw_response = json.dumps(fallback_data, ensure_ascii=False)
        result = self.validator.validate(news, filter_result, raw_response)

        # fallback 结果也需要后处理
        result = self.post_processor.process(news, filter_result, result)

        return result

    def _identify_theme(self, text: str) -> str:
        """
        识别主题（简单规则）

        Args:
            text: 文本

        Returns:
            主题名称
        """
        if "机器人" in text or "人形机器人" in text:
            return "机器人"
        elif "英伟达" in text or "M10" in text:
            return "英伟达M10材料"
        elif "光模块" in text or "CPO" in text or "800G" in text:
            return "光模块/CPO"
        elif "芯片" in text or "半导体" in text:
            return "半导体"
        elif "AI" in text or "算力" in text:
            return "AI算力"
        elif "卫星" in text or "商业航天" in text:
            return "卫星产业"
        else:
            return ""

    def _identify_stocks(self, text: str) -> list[RelatedStock]:
        """
        识别关联股票（简单规则）

        Args:
            text: 文本

        Returns:
            关联股票列表
        """
        stocks = []

        for name, code in self.STOCK_MAPPING.items():
            if name in text:
                stocks.append(RelatedStock(
                    code=code,
                    name=name,
                    reason="新闻中提及该公司"
                ))

        return stocks


    def _clean_json_response(self, response: str) -> str:
        """
        清理 AI 返回的 JSON 响应，去除代码块包裹

        Args:
            response: 原始响应

        Returns:
            清理后的 JSON 字符串
        """
        import re

        response = response.strip()

        # 去除 ```json ... ``` 包裹
        if response.startswith("```"):
            # 匹配 ```json 或 ```
            response = re.sub(r'^```(?:json)?\s*\n?', '', response)
            response = re.sub(r'\n?```\s*$', '', response)

        return response.strip()


__all__ = ['AIEventExtractor']
