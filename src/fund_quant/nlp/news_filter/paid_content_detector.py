"""
付费内容检测器
识别付费标题和隐藏股票，用于降权处理
"""
from dataclasses import dataclass, field
from typing import List


# 付费标题前缀
PAID_TITLE_PREFIXES = [
    "【风口研报",
    "【财联社早知道】",
    "【电报解读】",
    "【公告全知道】",
    "【盘中宝】",
    "【九点特供】",
    "【研选】",
    "【狙击龙虎榜】",
    "【机构调研】",
    "【VIP机会】",
]

# 付费研报关键词（更广泛的识别）
PAID_RESEARCH_KEYWORDS = [
    "电报解读",
    "风口研报",
    "公告全知道",
    "盘中宝",
    "狙击龙虎榜",
    "研报",
    "强call",
    "这家公司",
    "该公司",
    "公司正加快",
    "业内称",
    "分析师称",
    # 新增
    "研选",
    "研报数据",
    "研选•研报数据",
    "研选·研报数据",
    "研报精选",
    "机构称",
    "分析师强call",
    "公司晋身",
    "充分受益",
    "迎共振式增长",
    "公司产品",
    "公司客户",
    "公司正",
    "拟受益",
    "有望受益",
]

# 隐藏股票短语
HIDDEN_STOCK_PHRASES = [
    "这家公司",
    "这家小而美",
    '这家"小而美"',
    "另有家公司",
    "另有公司",
    "相关公司",
    "A公司",
    "B公司",
    "该公司",
    "公司之一",
]


@dataclass
class PaidContentResult:
    """付费内容检测结果"""
    content_status: str  # full_text/empty_content/paid_locked/title_only/summary_only
    is_paid_locked: bool
    is_title_only_signal: bool
    stock_visibility: str  # visible/hidden_by_paid_content/unknown
    theme_eligible: bool
    trade_eligible: bool
    score_cap_reason: str = ""
    matched_prefix: str = ""
    matched_hidden_phrases: List[str] = field(default_factory=list)


class PaidContentDetector:
    """
    付费内容检测器

    职责：
    1. 识别付费标题
    2. 检测隐藏股票短语
    3. 判断内容可见性
    """

    def __init__(self):
        """初始化"""
        self.paid_prefixes = PAID_TITLE_PREFIXES
        self.hidden_phrases = HIDDEN_STOCK_PHRASES

    def detect(self, title: str, content: str = "") -> PaidContentResult:
        """
        检测付费内容

        Args:
            title: 新闻标题
            content: 新闻正文

        Returns:
            PaidContentResult
        """
        # 检查付费标题前缀
        matched_prefix = ""
        is_paid_title = False
        for prefix in self.paid_prefixes:
            if title.startswith(prefix):
                matched_prefix = prefix
                is_paid_title = True
                break

        # 检查隐藏股票短语
        matched_hidden = []
        for phrase in self.hidden_phrases:
            if phrase in title:
                matched_hidden.append(phrase)

        # 判断内容状态
        content_length = len(content.strip()) if content else 0

        if is_paid_title:
            if content_length == 0:
                # 付费标题且无正文
                return PaidContentResult(
                    content_status="paid_locked",
                    is_paid_locked=True,
                    is_title_only_signal=True,
                    stock_visibility="hidden_by_paid_content" if matched_hidden else "unknown",
                    theme_eligible=True,
                    trade_eligible=False,
                    score_cap_reason="paid_locked_hidden_stock" if matched_hidden else "paid_locked",
                    matched_prefix=matched_prefix,
                    matched_hidden_phrases=matched_hidden
                )
            elif content_length < 80:
                # 付费标题且正文很短
                return PaidContentResult(
                    content_status="summary_only",
                    is_paid_locked=True,
                    is_title_only_signal=True,
                    stock_visibility="hidden_by_paid_content" if matched_hidden else "unknown",
                    theme_eligible=True,
                    trade_eligible=False,
                    score_cap_reason="paid_locked_summary_only",
                    matched_prefix=matched_prefix,
                    matched_hidden_phrases=matched_hidden
                )
            else:
                # 付费标题但有较长正文（VIP解锁或泄露）
                return PaidContentResult(
                    content_status="full_text",
                    is_paid_locked=True,
                    is_title_only_signal=False,
                    stock_visibility="visible",
                    theme_eligible=True,
                    trade_eligible=False,  # 仍然是付费内容
                    score_cap_reason="paid_locked_with_visible_stock",
                    matched_prefix=matched_prefix,
                    matched_hidden_phrases=matched_hidden
                )
        else:
            # 非付费标题
            if matched_hidden:
                stock_visibility = "hidden_by_paid_content"
            else:
                stock_visibility = "visible" if content_length > 0 else "unknown"

            return PaidContentResult(
                content_status="full_text" if content_length > 0 else "empty_content",
                is_paid_locked=False,
                is_title_only_signal=False,
                stock_visibility=stock_visibility,
                theme_eligible=True,
                trade_eligible=True,
                matched_prefix="",
                matched_hidden_phrases=matched_hidden
            )


def is_paid_research_teaser(text: str) -> bool:
    """
    判断是否为付费研报标题

    Args:
        text: 标题或完整文本

    Returns:
        是否为付费研报
    """
    return any(kw in text for kw in PAID_RESEARCH_KEYWORDS)


def classify_paid_research_teaser(item: dict) -> dict:
    """
    付费研报分类

    处理原则：
    1. event_type = "paid_research_teaser"
    2. ai_level = "light"
    3. need_ai = True
    4. trade_priority = "watch"
    5. confidence = 0.55
    6. can_trade_directly = False
    7. need_manual_followup = True
    8. 如果标题没有明确股票代码，related_stocks = []

    Args:
        item: 新闻 item dict

    Returns:
        增强后的 item
    """
    # 基础字段
    item['event_type'] = 'paid_research_teaser'
    item['ai_level'] = 'light'
    item['need_ai'] = True
    item['trade_priority'] = 'watch'
    item['confidence'] = 0.55
    item['can_trade_directly'] = False
    item['need_manual_followup'] = True
    item['manual_followup_reason'] = '标题隐藏公司名，正文为空或信息不完整，无法确认标的'

    # 风险标记
    risk_flags = item.get('risk_flags', [])
    if 'teaser_no_full_content' not in risk_flags:
        risk_flags.append('teaser_no_full_content')
    if 'hidden_stock' not in risk_flags:
        risk_flags.append('hidden_stock')
    item['risk_flags'] = risk_flags

    # final_score 默认 55
    if 'final_score' not in item or item['final_score'] == 0:
        item['final_score'] = 55

    # 主题提取（简单规则，从标题提取）
    title = item.get('title', '')
    content = item.get('content', '')
    text = f"{title} {content}".lower()

    theme_ids = []
    theme_names = []

    # AI 算力相关
    if any(kw in text for kw in ['ai', '算力', '铜箔', 'hvlp', 'gpu', '芯片', '数据中心', 'ai超级周期']):
        if 'ai_compute' not in theme_ids:
            theme_ids.append('ai_compute')
            theme_names.append('AI算力')

    # 光模块/光芯片
    if any(kw in text for kw in ['光模块', '光通信', '高速背板', '光互连', '光芯片', '光芯片需求']):
        if 'optical_module' not in theme_ids:
            theme_ids.append('optical_module')
            theme_names.append('光模块')

    # 液冷
    if any(kw in text for kw in ['液冷', '散热', '冷板']):
        if 'liquid_cooling' not in theme_ids:
            theme_ids.append('liquid_cooling')
            theme_names.append('液冷')

    # PCB/铜箔
    if any(kw in text for kw in ['pcb', '铜箔', 'hvlp', '高速背板']):
        if 'pcb_material' not in theme_ids:
            theme_ids.append('pcb_material')
            theme_names.append('PCB材料')
        if 'copper_foil' not in theme_ids:
            theme_ids.append('copper_foil')
            theme_names.append('铜箔')

    # 半导体材料
    if any(kw in text for kw in ['半导体材料', '关键材料体系', '磷化铟', 'inp', 'low-dk', 'low dk', 'low cte']):
        if 'semiconductor_material' not in theme_ids:
            theme_ids.append('semiconductor_material')
            theme_names.append('半导体材料')

    # 磷化铟
    if '磷化铟' in text or 'inp' in text:
        if 'inp' not in theme_ids:
            theme_ids.append('inp')
            theme_names.append('磷化铟')

    # Low-Dk材料
    if any(kw in text for kw in ['low-dk', 'low dk', 'low cte', '二代布', '布龙头']):
        if 'low_dk_material' not in theme_ids:
            theme_ids.append('low_dk_material')
            theme_names.append('Low-Dk材料')

    # MLCC
    if 'mlcc' in text:
        if 'mlcc' not in theme_ids:
            theme_ids.append('mlcc')
            theme_names.append('MLCC')

    # 半导体
    if any(kw in text for kw in ['半导体', '芯片', 'gpu', '国产gpu']):
        if 'semiconductor' not in theme_ids:
            theme_ids.append('semiconductor')
            theme_names.append('半导体')

    # 机器人
    if '机器人' in text:
        if 'robot' not in theme_ids:
            theme_ids.append('robot')
            theme_names.append('机器人')

    # 商业航天
    if any(kw in text for kw in ['商业航天', '卫星', '火箭']):
        if 'commercial_space' not in theme_ids:
            theme_ids.append('commercial_space')
            theme_names.append('商业航天')

    item['theme_ids'] = theme_ids
    item['theme_names'] = theme_names

    # 催化剂判断
    if '订单' in text or '在手订单' in text:
        item['catalyst'] = 'order_visibility_and_sample_validation'
    elif '送样' in text or '验证' in text:
        item['catalyst'] = 'sample_validation'
    elif '扩产' in text or '量产' in text:
        item['catalyst'] = 'capacity_expansion'
    elif '研报' in text or '强call' in text or '研选' in text:
        item['catalyst'] = 'research_recommendation'
    elif '共振式增长' in text or '窗口期' in text:
        item['catalyst'] = 'industry_trend'
    else:
        item['catalyst'] = 'industry_trend'

    # 供应链位置（简单判断）
    if any(kw in text for kw in ['光芯片', '磷化铟', 'low-dk', '二代布']):
        item['supply_chain_position'] = 'AI光芯片与高速材料'
    elif any(kw in text for kw in ['铜箔', '光模块', '液冷', 'mlcc', 'pcb']):
        item['supply_chain_position'] = 'AI服务器高速互连与散热'
    elif '芯片' in text or 'gpu' in text:
        item['supply_chain_position'] = 'AI芯片'
    else:
        item['supply_chain_position'] = ''

    return item


__all__ = [
    'PaidContentDetector',
    'PaidContentResult',
    'PAID_TITLE_PREFIXES',
    'PAID_RESEARCH_KEYWORDS',
    'HIDDEN_STOCK_PHRASES',
    'is_paid_research_teaser',
    'classify_paid_research_teaser',
]
