"""
AI 输出后处理器 - 将不稳定的 AI 原始输出转换为稳定的结构化结果
"""
import re
from typing import Any


class AIOutputPostProcessor:
    """
    AI 输出后处理器

    职责：
    1. 字段归一化：event_level "B级" -> "B"
    2. 规则纠偏：sentiment 根据关键词纠正
    3. 主题补全：themes 从关键词词典补全
    4. 置信度重算：根据修正情况调整 confidence
    """

    # 标准主题列表
    STANDARD_THEMES = {
        "英伟达供应链",
        "PCB",
        "光模块",
        "AI服务器",
        "先进封装",
        "机器人",
        "卫星互联网",
        "新能源车",
        "半导体",
        "低空经济",
        "算力"
    }

    # 主题词典
    THEME_KEYWORDS = {
        "英伟达供应链": [
            "英伟达", "nvidia", "rubin", "blackwell",
            "gb200", "gb300", "m9", "m10"
        ],
        "PCB": [
            "pcb", "覆铜板", "ccl", "印制电路板",
            "高频高速板", "高速覆铜板", "hvlp", "low dk", "low df"
        ],
        "AI服务器": [
            "ai服务器", "服务器", "算力服务器", "液冷服务器",
            "nvl", "机架", "rubin机架", "blackwell机架"
        ],
        "光模块": [
            "光模块", "800g", "1.6t", "cpo", "硅光",
            "光通信", "光芯片", "激光器"
        ],
        "先进封装": [
            "cowos", "hbm", "abf", "玻璃基板",
            "硅中介层", "先进封装", "chiplet"
        ],
        "机器人": [
            "人形机器人", "机器人", "灵巧手", "减速器",
            "丝杠", "执行器", "关节模组"
        ],
        "卫星互联网": [
            "卫星互联网", "低轨卫星", "商业航天",
            "星链", "卫星通信"
        ],
        "新能源车": [
            "新能源车", "智能驾驶", "车载", "域控",
            "线控底盘", "高压快充", "充电桩"
        ],
        "半导体": [
            "半导体", "晶圆", "芯片", "eda",
            "光刻胶", "存储", "dram", "nand", "hbm"
        ],
        "低空经济": [
            "低空经济", "evtol", "飞行汽车", "无人机"
        ],
        "算力": [
            "算力", "数据中心", "gpu", "aidc", "液冷", "idc"
        ]
    }

    # positive 关键词（A 股语义）
    POSITIVE_KEYWORDS = [
        "送样", "通过验证", "验证通过", "量产", "批量供货", "供货",
        "中标", "订单", "签约", "涨价", "扩产", "突破", "导入",
        "客户认证", "获得认证", "进入供应链", "定点", "项目定点", "放量"
    ]

    # negative 关键词（优先级高）
    NEGATIVE_KEYWORDS = [
        "澄清", "暂无", "不涉及", "未涉及", "否认", "传闻不实",
        "减持", "处罚", "亏损", "下修", "终止", "取消", "延期",
        "暂停", "立案", "调查", "风险提示"
    ]

    def process(
        self,
        title: str,
        content: str | None,
        ai_result: dict | None,
        rule_result: dict | None = None,
    ) -> dict:
        """
        处理 AI 原始输出，返回规范化的最终结果

        Args:
            title: 新闻标题
            content: 新闻正文
            ai_result: AI 原始输出（dict）
            rule_result: 规则抽取结果（可选）

        Returns:
            规范化的最终结果 dict
        """
        text = f"{title} {content or ''}"
        corrections = []

        # 如果 AI 结果为空，完全基于规则
        if not ai_result:
            ai_result = {}

        # 0. 修复 AI 误把 event_level 填到 event_type
        raw_event_type = ai_result.get("event_type", "")
        if str(raw_event_type).strip() in {"A", "B", "C", "A级", "B级", "C级"}:
            # AI 把 event_level 填到了 event_type
            if not ai_result.get("event_level"):
                ai_result["event_level"] = raw_event_type
            ai_result["event_type"] = ""  # 清空，后面会根据关键词推断
            corrections.append("event_type_level_misplaced_fixed")

        # 1. 归一化 event_level
        raw_event_level = ai_result.get("event_level", "")
        event_level = self.normalize_event_level(raw_event_level)
        if str(raw_event_level) != event_level:
            corrections.append("event_level_normalized")

        # 2. 归一化 sentiment
        raw_sentiment = ai_result.get("sentiment", "")
        normalized_sentiment = self.normalize_sentiment(raw_sentiment)
        if str(raw_sentiment) != normalized_sentiment:
            corrections.append("sentiment_normalized")

        # 3. 根据关键词纠偏 sentiment
        sentiment, sentiment_corrections = self.correct_sentiment_by_rules(
            text, normalized_sentiment
        )
        corrections.extend(sentiment_corrections)

        # 4. 归一化 themes
        raw_themes = ai_result.get("themes", []) or ai_result.get("theme", [])
        normalized_themes = self.normalize_themes(raw_themes)
        if raw_themes != normalized_themes:
            corrections.append("themes_normalized")

        # 5. 从关键词补全 themes
        keyword_themes = self.extract_themes_by_keywords(text)

        # 6. 合并 themes
        rule_themes = []
        if rule_result and "themes" in rule_result:
            rule_themes = rule_result.get("themes", [])

        merged_themes = self.merge_themes(rule_themes, normalized_themes, keyword_themes)

        # 7. 过滤标准主题和非标准主题
        standard_themes, non_standard_themes = self.filter_standard_themes(merged_themes)

        if keyword_themes and not normalized_themes:
            corrections.append("themes_filled_by_keyword")

        # 8. 归一化 event_type
        raw_event_type = ai_result.get("event_type", "")
        event_type = self.normalize_event_type(raw_event_type, text)
        if raw_event_type and raw_event_type != event_type:
            corrections.append("event_type_corrected_by_keyword")

        # 9. 重算 confidence
        raw_confidence = ai_result.get("confidence", 0.5)
        confidence = self.calculate_confidence(
            raw_confidence=raw_confidence,
            ai_result=ai_result,
            corrections=corrections,
            event_type=event_type,
            sentiment=sentiment,
            themes=standard_themes,
            title=title
        )
        if abs(confidence - self._parse_confidence(raw_confidence)) > 0.05:
            corrections.append("confidence_recalculated")

        # 9.5 过滤 related_stocks 中的人名
        related_stocks = ai_result.get("related_stocks", [])
        if related_stocks:
            filtered_stocks = self.filter_person_names_from_stocks(related_stocks)
            ai_result["related_stocks"] = filtered_stocks

        # 10. 获取或初始化 sub_themes
        sub_themes = ai_result.get("sub_themes", []) or []
        if isinstance(sub_themes, str):
            sub_themes = [sub_themes] if sub_themes else []

        # 将非标准主题添加到 sub_themes
        for theme in non_standard_themes:
            if theme not in sub_themes:
                sub_themes.append(theme)

        # 11. 构造最终结果
        final_result = {
            "event_type": event_type,
            "event_level": event_level,
            "sentiment": sentiment,
            "themes": standard_themes,  # 只包含标准主题
            "theme": ", ".join(standard_themes) if standard_themes else "",  # 向后兼容
            "sub_themes": sub_themes,  # 非标准主题放这里
            "confidence": confidence,
            "reason": ai_result.get("reason", "") or ai_result.get("summary", ""),
            "corrections": corrections,
            "ai_raw_result": ai_result
        }

        # 保留其他 AI 字段（向后兼容）
        for key in ["summary", "related_stocks", "risk_flags", "novelty_type", "is_market_relevant"]:
            if key in ai_result:
                final_result[key] = ai_result[key]

        return final_result

    def normalize_event_level(self, value: Any) -> str:
        """
        归一化 event_level

        支持：
        - "A级" / "A类" / "Level A" / "高/A" -> "A"
        - "B级" / "B/C" / "Level B" / "中等/B" -> "B"
        - "C级" / "Level C" / "低/C" -> "C"
        - "A/B" -> "A" (优先高级别)
        - "B/C" -> "B" (优先高级别)
        """
        if not value:
            return "C"

        value_str = str(value).upper().strip()

        # 精确匹配
        if value_str in ["A", "B", "C"]:
            return value_str

        # 包含 A（优先级最高）
        if "A" in value_str:
            return "A"

        # 包含 B
        if "B" in value_str:
            return "B"

        # 包含 C
        if "C" in value_str:
            return "C"

        # 无法识别，默认 C
        return "C"

    def normalize_sentiment(self, value: Any) -> str:
        """
        归一化 sentiment

        支持：
        - positive / 利好 / 正面 / 积极
        - negative / 利空 / 负面 / 消极
        - neutral / 中性 / 一般 / 未知
        """
        if not value:
            return "neutral"

        value_str = str(value).lower().strip()

        # 英文
        if value_str in ["positive", "pos"]:
            return "positive"
        if value_str in ["negative", "neg"]:
            return "negative"
        if value_str in ["neutral", "neu"]:
            return "neutral"

        # 中文
        if value_str in ["利好", "正面", "积极"]:
            return "positive"
        if value_str in ["利空", "负面", "消极"]:
            return "negative"
        if value_str in ["中性", "一般", "未知"]:
            return "neutral"

        # 模糊匹配
        if "positive" in value_str or "正" in value_str or "好" in value_str:
            return "positive"
        if "negative" in value_str or "负" in value_str or "空" in value_str:
            return "negative"

        return "neutral"

    def correct_sentiment_by_rules(
        self, text: str, ai_sentiment: str
    ) -> tuple[str, list[str]]:
        """
        根据 A 股新闻关键词纠偏 sentiment

        规则：
        - 风险解除类关键词 -> positive（优先级最高）
        - negative 关键词优先级次高
        - 然后是 positive 关键词
        - 最后保留 AI 的判断

        Returns:
            (最终 sentiment, corrections)
        """
        text_lower = text.lower()
        corrections = []

        # 检查风险解除类关键词（最高优先级）
        risk_removed_keywords = ["撤销退市风险警示", "撤销其他风险警示", "摘帽"]
        for keyword in risk_removed_keywords:
            if keyword in text_lower:
                if ai_sentiment != "positive":
                    corrections.append("sentiment_corrected_by_keyword")
                return "positive", corrections

        # 检查 negative 关键词（次高优先级）
        for keyword in self.NEGATIVE_KEYWORDS:
            if keyword in text_lower:
                if ai_sentiment != "negative":
                    corrections.append("sentiment_corrected_by_keyword")
                return "negative", corrections

        # 检查 positive 关键词
        for keyword in self.POSITIVE_KEYWORDS:
            if keyword in text_lower:
                if ai_sentiment != "positive":
                    corrections.append("sentiment_corrected_by_keyword")
                return "positive", corrections

        # 没有命中关键词，保留 AI 判断
        return ai_sentiment, corrections

    def normalize_themes(self, value: Any) -> list[str]:
        """
        归一化 themes，确保返回 list[str]

        支持：
        - "" -> []
        - None -> []
        - "PCB" -> ["PCB"]
        - "PCB,英伟达供应链" -> ["PCB", "英伟达供应链"]
        - ["PCB", "", None] -> ["PCB"]
        """
        if not value:
            return []

        # 已经是列表
        if isinstance(value, list):
            # 过滤空值，去重
            themes = []
            seen = set()
            for item in value:
                if item and str(item).strip():
                    theme = str(item).strip()
                    if theme not in seen:
                        themes.append(theme)
                        seen.add(theme)
            return themes

        # 字符串，尝试分割
        value_str = str(value).strip()
        if not value_str:
            return []

        # 尝试按逗号、顿号、分号分割
        themes = re.split(r'[,，、;；]', value_str)
        themes = [t.strip() for t in themes if t.strip()]

        # 去重，保持顺序
        seen = set()
        result = []
        for theme in themes:
            if theme not in seen:
                result.append(theme)
                seen.add(theme)

        return result

    def extract_themes_by_keywords(self, text: str) -> list[str]:
        """
        从文本中根据关键词提取主题

        Returns:
            匹配到的主题列表（去重，保持顺序）
        """
        text_lower = text.lower()
        themes = []
        seen = set()

        for theme_name, keywords in self.THEME_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if theme_name not in seen:
                        themes.append(theme_name)
                        seen.add(theme_name)
                    break

        return themes

    def merge_themes(
        self,
        rule_themes: list[str],
        ai_themes: list[str],
        keyword_themes: list[str]
    ) -> list[str]:
        """
        合并主题

        优先级：
        1. 规则识别的主题（最高）
        2. 关键词识别的主题
        3. AI 识别的主题（最低）

        去重，保持顺序
        """
        themes = []
        seen = set()

        # 1. 规则主题
        for theme in rule_themes:
            if theme and theme not in seen:
                themes.append(theme)
                seen.add(theme)

        # 2. 关键词主题
        for theme in keyword_themes:
            if theme and theme not in seen:
                themes.append(theme)
                seen.add(theme)

        # 3. AI 主题
        for theme in ai_themes:
            if theme and theme not in seen:
                themes.append(theme)
                seen.add(theme)

        return themes

    def filter_standard_themes(
        self,
        themes: list[str]
    ) -> tuple[list[str], list[str]]:
        """
        过滤标准主题和非标准主题

        Args:
            themes: 所有主题列表

        Returns:
            (标准主题列表, 非标准主题列表)
        """
        standard = []
        non_standard = []

        for theme in themes:
            if theme in self.STANDARD_THEMES:
                standard.append(theme)
            else:
                non_standard.append(theme)

        return standard, non_standard

    def normalize_event_type(self, value: Any, text: str) -> str:
        """
        归一化 event_type

        优先根据关键词判断，AI 输出作为参考
        """
        text_lower = text.lower()

        # 1. 宏观金融类（最高优先级，避免误判为普通事件）
        if any(kw in text_lower for kw in ["国债", "附息", "财政部", "债券发行", "续发行", "招标面值"]):
            return "bond_issue"

        if any(kw in text_lower for kw in ["汇率", "美元兑", "人民币兑", "外汇", "福林"]):
            return "fx_move"

        # 2. 地缘政治类
        if any(kw in text_lower for kw in ["美伊", "g7", "七国集团", "峰会", "停火", "地缘"]):
            return "geopolitics"

        # 3. 海外市场类
        if any(kw in text_lower for kw in ["评级上调", "升至买入", "目标价上调"]):
            return "rating_upgrade"

        if any(kw in text_lower for kw in ["评级下调", "降至卖出", "目标价下调"]):
            return "rating_downgrade"

        if any(kw in text_lower for kw in ["股价上涨", "股价下跌", "美股盘前", "盘前涨", "盘前跌"]):
            return "stock_price_move"

        # 4. 运营数据类
        if any(kw in text_lower for kw in ["合约销售", "销售金额", "前", "个月销售"]) and "销售" in text_lower:
            return "sales_data"

        if any(kw in text_lower for kw in ["经营数据", "运营数据"]):
            return "operating_update"

        # 5. 公司行为类
        # 减持优先级高于回购
        if any(kw in text_lower for kw in ["减持", "持股比例降至"]):
            return "shareholder_reduction"

        if any(kw in text_lower for kw in ["回购", "股份回购", "a股回购", "h股回购", "耗资回购"]):
            return "share_buyback"

        if any(kw in text_lower for kw in ["控股股东", "股份转让", "协议转让", "控制权变更", "实控人变更", "过户完成"]):
            return "control_change"

        if any(kw in text_lower for kw in ["控制权变更终止", "股份转让协议解除", "控制权终止"]):
            return "control_change_terminated"

        # 6. 风险事件
        # 风险解除/摘帽（positive）
        if any(kw in text_lower for kw in ["撤销退市风险警示", "撤销其他风险警示", "摘帽", "股票简称变更为"]):
            return "risk_warning_removed"

        # 审查调查事件
        if any(kw in text_lower for kw in ["接受审查调查", "纪律审查", "监察调查", "涉嫌严重违纪违法", "立案调查", "被查"]):
            return "regulatory_investigation"

        # 风险澄清（negative）
        if any(kw in text_lower for kw in ["澄清", "暂无", "不涉及", "否认", "传闻不实"]):
            return "risk_disconfirm"

        # 7. A 股产业事件
        # price_increase 优先级最高（避免被其他事件覆盖）
        if any(kw in text_lower for kw in ["涨价", "提价", "价格上调", "上调约", "服务上调", "价格上涨"]) and "股价" not in text_lower:
            return "price_increase"

        if any(kw in text_lower for kw in ["送样"]):
            return "sample_delivery"

        # mass_production 只用于真正的量产，不用于销售数据
        if any(kw in text_lower for kw in ["量产", "批量供货", "放量生产", "投产"]) and "销售" not in text_lower:
            return "mass_production"

        if any(kw in text_lower for kw in ["订单", "中标", "定点", "项目定点"]):
            return "order_win"

        if any(kw in text_lower for kw in ["扩产", "产能"]) and "销售" not in text_lower:
            return "capacity_build"

        if any(kw in text_lower for kw in ["突破", "首发", "研发成功", "通过验证", "验证通过"]):
            return "verification_pass"

        # strategic_cooperation 只用于公司间合作
        if any(kw in text_lower for kw in ["签约", "合同", "战略合作"]) and not any(kw in text_lower for kw in ["美伊", "g7", "峰会"]):
            return "strategic_cooperation"

        # 8. 高管普通变动
        if any(kw in text_lower for kw in ["选举董事长", "聘任总经理", "聘任副总经理", "董事会换届", "高管变动"]):
            return "management_change"

        # 9. 政策类
        if any(kw in text_lower for kw in ["央行", "监管办法", "征求意见"]):
            return "macro_policy"

        if any(kw in text_lower for kw in ["政策发布", "政策落地", "通知", "指导意见", "规划"]):
            return "policy_release"

        # 如果 AI 有输出且有效，使用 AI 的
        if value and str(value).strip() and str(value).strip() not in {"A", "B", "C", "A级", "B级", "C级"}:
            return str(value).strip()

        return "general"

    def calculate_confidence(
        self,
        raw_confidence: Any,
        ai_result: dict,
        corrections: list[str],
        event_type: str,
        sentiment: str,
        themes: list[str],
        title: str = ""
    ) -> float:
        """
        重新计算 confidence

        基础分：AI 的 confidence（默认 0.5）

        加分项：
        - event_type 被关键词识别：+0.15
        - sentiment 被关键词识别：+0.10
        - themes 被关键词识别：+0.10
        - event_level 成功归一化：+0.05

        减分项：
        - AI 字段缺失：-0.10
        - AI themes 类型错误：-0.05
        - AI sentiment 与规则冲突：-0.10
        - AI event_level 非标准：-0.05

        上限规则：
        - related_stocks 缺 code：最大 0.85
        - themes 为空：最大 0.80
        - 标题为空：最大 0.60
        - event_type 被强制修正：最大 0.85
        - 非 A 股市场（宏观/海外/债券/外汇）：最大 0.75

        限制在 0.0 ~ 1.0
        """
        base = self._parse_confidence(raw_confidence)
        confidence = base

        # 加分项
        if "event_type_corrected_by_keyword" in corrections:
            confidence += 0.15

        if "sentiment_corrected_by_keyword" in corrections:
            confidence += 0.10

        if "themes_filled_by_keyword" in corrections and themes:
            confidence += 0.10

        if "event_level_normalized" in corrections:
            confidence += 0.05

        # 减分项
        if not ai_result.get("event_type"):
            confidence -= 0.10

        if "themes_normalized" in corrections:
            confidence -= 0.05

        if "sentiment_corrected_by_keyword" in corrections:
            # 说明 AI 判断与规则冲突
            confidence -= 0.10

        if "event_level_normalized" in corrections:
            # 说明 AI 输出非标准
            confidence -= 0.05

        # 限制范围
        confidence = max(0.0, min(1.0, confidence))

        # 应用上限规则
        # 1. 标题为空
        if not title or not title.strip():
            confidence = min(confidence, 0.60)

        # 2. themes 为空
        if not themes:
            confidence = min(confidence, 0.80)

        # 3. event_type 被强制修正
        if "event_type_corrected_by_keyword" in corrections:
            confidence = min(confidence, 0.85)

        # 4. related_stocks 缺 code
        related_stocks = ai_result.get("related_stocks", [])
        if related_stocks:
            has_missing_code = any(not stock.get("code") for stock in related_stocks if isinstance(stock, dict))
            if has_missing_code:
                confidence = min(confidence, 0.85)

        # 5. 非 A 股市场事件
        non_a_share_types = {
            "bond_issue", "fx_move", "geopolitics", "rating_upgrade",
            "rating_downgrade", "stock_price_move", "macro_policy"
        }
        if event_type in non_a_share_types:
            confidence = min(confidence, 0.75)

        # 6. event_type/event_level 字段混淆被修正
        if "event_type_level_misplaced_fixed" in corrections:
            confidence = min(confidence, 0.75)

        return round(confidence, 2)

    def filter_person_names_from_stocks(self, related_stocks: list) -> list:
        """
        过滤 related_stocks 中的人名

        Args:
            related_stocks: AI 输出的 related_stocks 列表

        Returns:
            过滤后的列表
        """
        if not related_stocks:
            return []

        filtered = []
        for stock in related_stocks:
            if not isinstance(stock, dict):
                continue

            name = stock.get("name", "")
            if not name:
                continue

            # 简单启发式判断人名：
            # 1. 长度 2-4 字符
            # 2. 不包含"公司"、"集团"、"股份"、"有限"、"银行"、"科技"等
            # 3. 不包含英文字母（排除股票代码）
            company_keywords = ["公司", "集团", "股份", "有限", "银行", "科技", "实业", "控股", "投资", "发展", "产业"]
            has_company_keyword = any(kw in name for kw in company_keywords)
            has_english = any(c.isalpha() for c in name)
            is_short = 2 <= len(name) <= 4

            # 如果看起来像人名（短且无公司关键词），跳过
            if is_short and not has_company_keyword and not has_english:
                continue

            filtered.append(stock)

        return filtered

    def _parse_confidence(self, value: Any) -> float:
        """解析 confidence，支持百分比、字符串数字"""
        if isinstance(value, (int, float)):
            # 如果是 0-100 范围，转成 0-1
            if value > 1.0:
                return value / 100.0
            return float(value)

        if isinstance(value, str):
            value = value.strip().replace("%", "")
            try:
                num = float(value)
                if num > 1.0:
                    return num / 100.0
                return num
            except ValueError:
                return 0.5

        return 0.5


__all__ = ['AIOutputPostProcessor']
