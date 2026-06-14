"""
AI 结果验证器
"""
import json
import re
from typing import Any

from fund_quant.nlp.news_ai.ai_event_models import AIEventResult, RelatedStock
from fund_quant.nlp.news_ai.prompt_builder import get_field


class AIResultValidator:
    """AI 结果验证器"""

    # 白名单定义
    VALID_EVENT_TYPES = [
        # A 股产业事件
        "order_win", "order_growth", "price_increase", "mass_production", "capacity_build",
        "verification_pass", "sample_delivery", "supply_chain",
        "product_release", "technical_breakthrough", "strategic_cooperation",
        "platform_launch", "benchmark_release", "dataset_release", "research_release",
        # 政策监管
        "policy_release", "macro_policy", "regional_policy",
        # 资本市场
        "mna", "ipo",
        # 风险事件
        "risk_disconfirm", "risk_warning_removed", "regulatory_investigation",
        # 公司行为
        "shareholder_reduction", "share_buyback", "control_change",
        "control_change_terminated", "management_change", "corporate_action",
        # 运营数据
        "sales_data", "operating_update",
        # 海外市场
        "rating_upgrade", "rating_downgrade", "stock_price_move",
        # 宏观金融
        "bond_issue", "fx_move", "geopolitics",
        # 行业活动
        "industry_activity", "trade_fair_result", "business_metric_growth",
        # 通用
        "general"
    ]

    # 事件类型映射（非白名单映射到白名单）
    EVENT_TYPE_MAPPING = {
        "news_update": "general",
        "company_update": "general",
        "announcement": "general"
    }

    VALID_SENTIMENTS = ["positive", "neutral", "negative"]
    VALID_EVENT_LEVELS = ["S", "A", "B", "C"]
    VALID_NOVELTY_TYPES = [
        "new_theme", "old_theme_new_progress", "old_theme_repeat",
        "negative_disconfirm", "noise"
    ]

    def validate(self, news: Any, filter_result: Any, raw_response: str) -> AIEventResult:
        """
        验证 AI 返回结果

        Args:
            news: 新闻对象
            filter_result: 过滤结果
            raw_response: AI 原始返回

        Returns:
            AIEventResult
        """
        news_id = get_field(news, 'news_id', '')
        action = get_field(filter_result, 'action', '')

        validation_errors = []

        # 尝试解析 JSON
        try:
            # 处理可能的代码块包裹
            cleaned_response = self._clean_response(raw_response)
            data = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            # JSON 解析失败
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
                raw_ai_response=raw_response,
                is_valid=False,
                validation_errors=[f"JSON解析失败: {str(e)}"]
            )

        # 检查必填字段（允许部分字段缺失并自动补充默认值）
        core_required_fields = [
            'event_type', 'sentiment', 'event_level', 'novelty_type'
        ]

        missing_core_fields = []
        for field in core_required_fields:
            if field not in data:
                missing_core_fields.append(field)

        # 如果缺少核心字段，返回失败结果
        if missing_core_fields:
            validation_errors.append(f"缺少核心必填字段: {', '.join(missing_core_fields)}")
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
                raw_ai_response=raw_response,
                is_valid=False,
                validation_errors=validation_errors
            )

        # 提取字段（允许缺失，使用默认值）
        is_market_relevant = data.get('is_market_relevant', True)
        event_type = data.get('event_type', 'general')

        # 优先使用 themes（list），向后兼容 theme（str）
        themes = data.get('themes', [])
        if not isinstance(themes, list):
            # 如果 themes 不是 list，尝试从 theme 解析
            theme_str = data.get('theme', '')
            if theme_str:
                themes = [t.strip() for t in str(theme_str).split(',') if t.strip()]
            else:
                themes = []

        # 生成向后兼容的 theme 字段（逗号分隔字符串）
        theme = data.get('theme', ', '.join(themes) if themes else '')

        sub_themes = data.get('sub_themes', [])
        sentiment = data.get('sentiment', 'neutral')
        event_level = data.get('event_level', 'C')
        novelty_type = data.get('novelty_type', 'noise')
        summary = data.get('summary', '')
        confidence = data.get('confidence', 0.0)
        risk_flags = data.get('risk_flags', [])

        # ===== 新增：字段类型严格校验 =====

        # 1. 校验 event_level 只能是 S/A/B/C
        if event_level not in self.VALID_EVENT_LEVELS:
            # 检查是否误填了 sentiment 值到 event_level
            if event_level in self.VALID_SENTIMENTS:
                validation_errors.append(f"event_level错误填写为sentiment值: {event_level}，已修正为C，sentiment设为{event_level}")
                sentiment = event_level  # 移动到sentiment
                event_level = "C"  # 修正为C
            else:
                validation_errors.append(f"非法 event_level: {event_level}，必须是 {self.VALID_EVENT_LEVELS}，已修正为C")
                event_level = "C"

        # 2. 校验 sentiment 只能是 positive/neutral/negative
        if sentiment not in self.VALID_SENTIMENTS:
            # 检查是否误填了 event_level 值到 sentiment
            if sentiment in self.VALID_EVENT_LEVELS:
                validation_errors.append(f"sentiment错误填写为event_level值: {sentiment}，已修正为neutral")
                sentiment = "neutral"
            else:
                validation_errors.append(f"非法 sentiment: {sentiment}，必须是 {self.VALID_SENTIMENTS}，已修正为neutral")
                sentiment = "neutral"

        # 记录缺失字段的警告（不影响 is_valid）
        # 不再对 theme 给警告，只要有 themes 就认为主题字段存在
        optional_fields = ['sub_themes', 'related_stocks', 'summary', 'confidence', 'risk_flags']
        for field in optional_fields:
            if field not in data:
                validation_errors.append(f"警告：缺少可选字段 {field}，已使用默认值")

        # 验证 themes 类型
        if not isinstance(themes, list):
            validation_errors.append(f"themes 必须是 list，当前类型: {type(themes)}")
            themes = []

        # 不再重复验证 sentiment 和 event_level（已在上面严格校验）

        # 验证 novelty_type
        if novelty_type not in self.VALID_NOVELTY_TYPES:
            validation_errors.append(f"非法 novelty_type: {novelty_type}，必须是 {self.VALID_NOVELTY_TYPES}")

        # 验证 event_type
        if event_type not in self.VALID_EVENT_TYPES:
            # 尝试映射到白名单
            if hasattr(self, 'EVENT_TYPE_MAPPING') and event_type in self.EVENT_TYPE_MAPPING:
                mapped_type = self.EVENT_TYPE_MAPPING[event_type]
                validation_errors.append(f"非法 event_type: {event_type}，已映射为 {mapped_type}")
                event_type = mapped_type
            else:
                validation_errors.append(f"非法 event_type: {event_type}，已修正为 general")
                event_type = "general"

        # 验证 confidence
        try:
            confidence = float(confidence)
            if confidence < 0.0 or confidence > 1.0:
                validation_errors.append(f"confidence 超出范围: {confidence}，必须在 0.0-1.0 之间")
        except (ValueError, TypeError):
            validation_errors.append(f"confidence 必须是数字: {confidence}")
            confidence = 0.0

        # 验证 sub_themes
        if not isinstance(sub_themes, list):
            validation_errors.append(f"sub_themes 必须是 list，当前类型: {type(sub_themes)}")
            sub_themes = []

        # 验证 related_stocks（增强：必须包含name/code/reason，否则删除）
        related_stocks_list = []
        if not isinstance(data.get('related_stocks', []), list):
            validation_errors.append(f"related_stocks 必须是 list")
        else:
            for idx, stock in enumerate(data.get('related_stocks', [])):
                if isinstance(stock, dict):
                    code = stock.get('code', '').strip()
                    name = stock.get('name', '').strip()
                    reason = stock.get('reason', '').strip()

                    # 必须包含name/code/reason，否则删除该条
                    if not name or not code or not reason:
                        validation_errors.append(f"related_stocks[{idx}] 缺少必填字段(name={name}, code={code}, reason={reason})，已删除")
                        continue  # 跳过该条

                    # 检查是否为非股票实体（国家、人物、机构）
                    # 这些应该在related_entities中，不应该在related_stocks
                    non_stock_keywords = ["中国", "美国", "伊朗", "议员", "总监", "部长", "大使", "商会", "协会", "医院", "政府"]
                    if any(kw in name for kw in non_stock_keywords):
                        validation_errors.append(f"related_stocks[{idx}] 包含非股票实体: {name}，应移到related_entities")
                        continue  # 跳过该条

                    related_stocks_list.append(RelatedStock(
                        code=code,
                        name=name,
                        reason=reason
                    ))
                else:
                    validation_errors.append(f"related_stocks[{idx}] 必须是 dict")

        # 特殊规则检查：risk 新闻不应为 positive
        if action == "risk" and sentiment == "positive":
            validation_errors.append("risk新闻不应被判断为positive")

        # 特殊规则检查：risk 新闻建议使用 negative_disconfirm
        if action == "risk" and novelty_type != "negative_disconfirm":
            validation_errors.append("risk新闻建议 novelty_type 使用 negative_disconfirm（警告）")

        # 一致性检查：送样/量产/中标/验证通过等应该是 positive + A级
        positive_events = ["sample_delivery", "mass_production", "order_win", "verification_pass", "price_increase"]
        if event_type in positive_events:
            if sentiment == "negative":
                validation_errors.append(f"{event_type} 事件不应为 negative sentiment")
            if event_level not in ["S", "A"]:
                validation_errors.append(f"{event_type} 事件通常应为 S 或 A 级，当前为 {event_level}")

        # 一致性检查：risk_disconfirm 应该是 negative
        if event_type == "risk_disconfirm" and sentiment == "positive":
            validation_errors.append("risk_disconfirm 事件不应为 positive sentiment")

        # 判断是否有效
        # 只有关键错误才算 is_valid=False
        # related_stocks 缺 code 只是警告，不影响 is_valid
        critical_errors = [
            err for err in validation_errors
            if not err.endswith("（警告）")
            and "警告" not in err
            and "缺少 code" not in err
            and "缺少 name" not in err
            and "缺少 reason" not in err
            and "缺少可选字段" not in err
        ]
        is_valid = len(critical_errors) == 0

        return AIEventResult(
            news_id=news_id,
            is_market_relevant=is_market_relevant,
            event_type=event_type,
            theme=theme,
            sub_themes=sub_themes,
            related_stocks=related_stocks_list,
            sentiment=sentiment,
            event_level=event_level,
            novelty_type=novelty_type,
            summary=summary,
            confidence=confidence,
            risk_flags=risk_flags,
            raw_ai_response=raw_response,
            is_valid=is_valid,
            validation_errors=validation_errors
        )

    def _clean_response(self, response: str) -> str:
        """
        清理 AI 返回的响应，去除可能的代码块包裹

        Args:
            response: 原始响应

        Returns:
            清理后的 JSON 字符串
        """
        # 去除首尾空白
        response = response.strip()

        # 如果被 ```json ... ``` 包裹，提取内容
        if response.startswith('```'):
            # 匹配 ```json 或 ``` 开头
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if match:
                response = match.group(1).strip()

        return response


__all__ = ['AIResultValidator']
