"""
AI 事件抽取 Prompt 构建器
"""
from typing import Any


def get_field(obj: Any, name: str, default=None):
    """
    兼容获取字段值

    支持：
    - dict
    - dataclass
    - 普通对象属性
    """
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class PromptBuilder:
    """Prompt 构建器"""

    # 事件类型白名单
    VALID_EVENT_TYPES = [
        # A 股产业事件
        "order_win",
        "price_increase",
        "mass_production",
        "capacity_build",
        "verification_pass",
        "sample_delivery",
        "supply_chain",
        "product_release",
        "technical_breakthrough",
        "strategic_cooperation",

        # 政策监管
        "policy_release",
        "macro_policy",

        # 资本市场
        "mna",
        "ipo",

        # 风险事件
        "risk_disconfirm",
        "risk_warning_removed",
        "regulatory_investigation",

        # 公司行为
        "shareholder_reduction",
        "share_buyback",
        "control_change",
        "control_change_terminated",
        "management_change",
        "corporate_action",

        # 运营数据
        "sales_data",
        "operating_update",

        # 海外市场
        "rating_upgrade",
        "rating_downgrade",
        "stock_price_move",

        # 宏观金融
        "bond_issue",
        "fx_move",
        "geopolitics",

        # 通用
        "general"
    ]

    def build(self, news: Any, filter_result: Any) -> str:
        """
        构建 prompt

        Args:
            news: 新闻对象（dataclass 或 dict）
            filter_result: 过滤结果（dataclass 或 dict）

        Returns:
            prompt 字符串
        """
        # 提取字段
        news_id = get_field(news, 'news_id', '')
        title = get_field(news, 'title', '')
        content = get_field(news, 'content', '')
        source = get_field(news, 'source', '')

        action = get_field(filter_result, 'action', '')
        pre_score = get_field(filter_result, 'pre_score', 0)
        matched_keywords = get_field(filter_result, 'matched_keywords', [])
        matched_rules = get_field(filter_result, 'matched_rules', [])
        reasons = get_field(filter_result, 'reasons', [])
        risk_flags = get_field(filter_result, 'risk_flags', [])

        # 截断内容（最多 1200 字）
        content_truncated = content[:1200] if content else ''

        # 构建过滤信息
        filter_info = f"""
过滤结果：
- 分类: {action}
- 预评分: {pre_score}
- 命中关键词: {', '.join(matched_keywords) if matched_keywords else '无'}
- 触发规则: {', '.join(matched_rules) if matched_rules else '无'}
- 判断理由: {'; '.join(reasons) if reasons else '无'}
- 风险标记: {', '.join(risk_flags) if risk_flags else '无'}
"""

        # 特殊提示（针对 risk 类型新闻）
        risk_warning = ""
        if action == "risk":
            risk_warning = """
⚠️ 重要提示：这是一条风险类新闻（包含澄清、证伪、利空等信息）
- 请重点判断是否是证伪或利空
- 不要因为出现题材词就误判为正面
- sentiment 必须为 negative
- event_type 应优先使用 risk_disconfirm
- novelty_type 应为 negative_disconfirm
"""

        # 构建完整 prompt
        prompt = f"""你是一个专业的量化交易新闻分析系统。请对以下新闻进行事件抽取。

新闻 ID: {news_id}
来源: {source}
标题: {title}
正文: {content_truncated}

{filter_info}
{risk_warning}

请严格按照以下要求输出 JSON（不要输出任何解释，不要使用 Markdown 代码块）：

事件级别定义：
- S级：重大政策、全球首个、产业链核心重大变化、重大并购、确认进入全球核心客户供应链
- A级：订单、中标、涨价、量产、验证通过、送样、进入供应链、重要客户合作、核心产品获批
- B级：新品发布、战略合作、扩产、技术突破、试点、示范项目
- C级：普通观点、一般会议、普通互动平台回复、泛泛表态

novelty_type 定义：
- new_theme：可能形成新题材
- old_theme_new_progress：老题材出现新进展
- old_theme_repeat：老题材重复信息
- negative_disconfirm：证伪/澄清/风险新闻
- noise：无交易价值噪音

event_type 必须从以下白名单选择：
{', '.join(self.VALID_EVENT_TYPES)}

输出 JSON 格式示例（⚠️ 下面仅展示格式，严禁照抄字段内容）：
{{
  "is_market_relevant": true或false,
  "event_type": "从白名单中选择，必须基于当前新闻",
  "event_level": "A" 或 "B" 或 "C"（只能是单个字母，不能是"A级"、"B/C"等）,
  "sentiment": "positive" 或 "negative" 或 "neutral"（只能是这三个英文单词）,
  "themes": ["主题1", "主题2"]（必须是数组，不能是字符串或空字符串）,
  "sub_themes": ["子主题1"],
  "related_stocks": [
    {{
      "code": "股票代码或空字符串",
      "name": "当前新闻中明确出现的公司名称",
      "reason": "必须基于当前新闻内容说明原因"
    }}
  ],
  "novelty_type": "从5种类型中选择",
  "summary": "用一句话总结当前新闻的核心事件",
  "confidence": 0.85,
  "risk_flags": []
}}

🔴 严格要求：
1. 上述示例仅表示 JSON 格式，不代表当前新闻内容
2. 严禁复制示例中的任何字段内容
3. 只能根据当前新闻的标题和正文进行抽取

4. event_level 只能输出单个字母：
   ✅ 正确："A"、"B"、"C"
   ❌ 错误："A级"、"B级"、"Level A"、"B/C"、"中等/B"

5. sentiment 只能输出三个英文单词之一：
   ✅ 正确："positive"、"negative"、"neutral"
   ❌ 错误："利好"、"正面"、"中性"、"积极"

6. themes 必须是数组，不能是字符串：
   ✅ 正确：["PCB", "英伟达供应链"]
   ✅ 正确：[]（无法识别时输出空数组）
   ❌ 错误：""（空字符串）
   ❌ 错误："PCB"（字符串）

7. A 股交易语义规则：
   - "送样"、"通过验证"、"量产"、"批量供货"、"中标"、"订单"、"定点"、"涨价"、"扩产" → positive
   - "澄清"、"暂无"、"不涉及"、"否认"、"传闻不实"、"减持"、"处罚"、"亏损" → negative
   - "专家表示"、"长期向好"、"建议关注"、"行业有望受益" → 低价值观点，event_level 应为 "C"

8. 当前新闻没有出现的公司，不能写入 related_stocks
9. 当前新闻没有出现的题材，不能写入 themes
10. 如果无法确定股票代码，code 使用空字符串
11. 如果当前新闻是澄清/暂无/不涉及/未量产/未形成收入，event_type 应优先使用 risk_disconfirm，sentiment 必须为 negative
12. confidence 必须是 0.0-1.0 之间的数字
13. 直接输出 JSON，不要使用 ```json 代码块
14. 不要输出任何解释性文本
"""

        return prompt


__all__ = ['PromptBuilder', 'get_field']
