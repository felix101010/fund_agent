"""
新闻过滤关键词规则
"""
import re
from typing import Optional

# 一、风险关键词（最高优先级）
# 注意：减持、处罚、亏损等不在此列，它们有专门的 event_type
# 风险关键词映射到 risk_flags
RISK_KEYWORDS = [
    "澄清",
    "暂无相关业务",
    "不涉及",
    "未涉及",
    "未开展",
    "未布局",
    "未量产",
    "尚未量产",
    "尚未形成收入",
    "未形成收入",
    "暂未产生收入",
    "尚未贡献收入",
    "收入占比较小",
    "对公司业绩影响较小",
    "风险提示",
    "交易风险",
    "股价异动",
    "问询函",
    "监管函",
    "关注函",
    "终止",
    "取消",
    "暂停",
    "延期",
    "业绩预减",
    "业绩亏损",
    "不及预期",
    "被实施退市风险警示",
    "被实施其他风险警示",
    "被ST",
    "被*ST",
    "接受审查调查",
    "纪律审查",
    "监察调查",
    "涉嫌严重违纪违法",
    "立案调查",
    "被查",
    "传闻",
    "网传",
    "未证实"
]

# 风险关键词到 risk_flag 的映射
RISK_KEYWORD_TO_FLAG = {
    "未形成收入": "not_recognized_revenue",
    "尚未形成收入": "not_recognized_revenue",
    "暂未产生收入": "not_recognized_revenue",
    "尚未贡献收入": "not_recognized_revenue",
    "收入占比较小": "not_recognized_revenue",
    "传闻": "rumor_or_unconfirmed",
    "网传": "rumor_or_unconfirmed",
    "未证实": "rumor_or_unconfirmed",
    "澄清": "negative_disconfirm",
    "不涉及": "negative_disconfirm",
    "未涉及": "negative_disconfirm",
    "暂无相关业务": "negative_disconfirm",
    "接受审查调查": "regulatory_risk",
    "立案调查": "regulatory_risk",
    "被查": "regulatory_risk",
    "问询函": "regulatory_risk",
    "监管函": "regulatory_risk",
    "纪律审查": "regulatory_risk",
    "监察调查": "regulatory_risk"
}

# 二、强事件关键词（高价值催化）
# 排除：国债招标等宏观金融类招标
# 注意："突破"已移除，需要上下文判断（避免"项目数突破600项"误判）
STRONG_EVENT_KEYWORDS = [
    "中标",
    "订单",
    "签订合同",
    "大单",
    "框架协议",
    "涨价",
    "提价",
    "调价",
    "量产",
    "投产",
    "扩产",
    "满产",
    "产能释放",
    "认证",
    "验证通过",
    "测试通过",
    "送样",
    "批量供货",
    "进入供应链",
    "供货",
    "独家供应",
    "唯一供应商",
    "A股第一",
    "国内首个",
    "全球首个",
    "行业首个",
    "技术突破",  # 明确为技术突破
    "核心技术突破",
    "关键技术突破",
    "并购",
    "重组",
    "收购",
    "IPO",
    "上市辅导",
    "政策发布",
    "政策落地",
    "补贴",
    "获批",
    "取得批文",
    "控股股东",
    "股份转让",
    "协议转让",
    "控制权变更",
    "实控人变更",
    "过户完成"
]

# 新增：业务指标关键词（数量突破，非技术突破）
BUSINESS_METRIC_KEYWORDS = [
    "项目数", "成交额", "参展人数", "客流量", "签约数",
    "票房", "用户数", "销售额", "规模", "数量", "订单数",
    "突破", "超过", "达到", "创新高"
]

# 新增：真实技术突破上下文关键词
TECH_BREAKTHROUGH_CONTEXT = [
    "技术突破", "核心技术", "关键技术", "国产替代", "首创",
    "研发成功", "攻克", "实现量产", "验证通过", "自主研发",
    "技术创新", "专利", "知识产权"
]

# 三、候选关键词（潜在题材/新方向）
CANDIDATE_KEYWORDS = [
    "新材料",
    "新工艺",
    "新平台",
    "新协议",
    "新模型",
    "新架构",
    "新路线",
    "新产品",
    "新技术",
    "国产替代",
    "替代进口",
    "自主可控",
    "核心零部件",
    "核心材料",
    "产业链",
    "供应链",
    "生态合作",
    "战略合作",
    "客户验证",
    "样品阶段",
    "小批量",
    "试生产",
    "试点",
    "示范项目",
    "商业化",
    "应用落地"
]

# 四、强实体关键词
STRONG_ENTITY_KEYWORDS = [
    "英伟达",
    "华为",
    "特斯拉",
    "苹果",
    "微软",
    "谷歌",
    "Meta",
    "OpenAI",
    "台积电",
    "三星",
    "SK海力士",
    "长鑫存储",
    "中芯国际",
    "寒武纪",
    "工业富联",
    "中际旭创",
    "新易盛",
    "生益科技",
    "沪电股份",
    "胜宏科技"
]

# 五、低价值关键词（低价值财经表达）
LOW_VALUE_KEYWORDS = [
    "专家表示",
    "业内人士表示",
    "机构认为",
    "券商认为",
    "有望受益",
    "长期向好",
    "未来可期",
    "空间广阔",
    "景气度提升",
    "持续推进",
    "加快推进",
    "积极布局",
    "一文看懂",
    "盘点",
    "复盘",
    "解读",
    "梳理",
    "概念股一览",
    "受关注",
    "热度提升",
    "研究显示",
    "论文显示",
    "科学家发现",
    "早期研究",
    "实验显示"
]

# 六、垃圾关键词（明显垃圾）
JUNK_KEYWORDS = [
    "广告",
    "优惠券",
    "抽奖",
    "直播带货",
    "娱乐",
    "明星",
    "综艺",
    "体育",
    "比赛",
    "旅游攻略",
    "美食",
    "情感",
    "星座"
]

# 八、宏观金融关键词（排除到低价值或单独分类）
MACRO_FINANCE_KEYWORDS = [
    "国债",
    "附息",
    "续发行",
    "招标面值",
    "财政部",
    "债券发行",
    "央行",
    "货币政策",
    "汇率",
    "美元兑",
    "人民币兑",
    "外汇",
    "利率",
    "加息",
    "降息",
    "存款准备金率"
]

# 九、海外市场关键词
OVERSEAS_MARKET_KEYWORDS = [
    "美股",
    "盘前",
    "盘后",
    "纳斯达克",
    "道琼斯",
    "标普",
    "港股",
    "恒生指数",
    "评级上调",
    "评级下调",
    "目标价",
    "升至买入",
    "降至卖出",
    "股价上涨",
    "股价下跌"
]

# 十、地缘政治关键词
GEOPOLITICS_KEYWORDS = [
    "美伊",
    "G7",
    "七国集团",
    "峰会",
    "外交",
    "停火",
    "制裁",
    "贸易战",
    "关税",
    "地缘"
]

# 十一、龙虎榜/市场数据关键词（无交易价值）
MARKET_DATA_KEYWORDS = [
    "龙虎榜",
    "两连板",
    "三连板",
    "四连板",
    "五连板",
    "六连板",
    "七连板",
    "八连板",
    "九连板",
    "十连板",
    "连板",
    "机构净买入",
    "机构净卖出",
    "游资",
    "营业部",
    "席位",
    "龙虎数据"
]

# 十二、高管普通变动关键词（低价值）
# 注意：被调查、辞职、失联等异常变动不在此列
EXEC_NORMAL_CHANGE_KEYWORDS = [
    "选举董事长",
    "聘任总经理",
    "聘任副总经理",
    "董事会换届",
    "监事会换届",
    "选举董事",
    "选举监事",
    "聘任财务总监",
    "聘任董事会秘书",
    "任期届满",
    "换届选举",
    "高管变动"
]

# 十三、社会治理/交通安全关键词（归档）
SOCIAL_GOVERNANCE_KEYWORDS = [
    "超员载客",
    "超速行驶",
    "务农务工",
    "出行安全",
    "交通安全",
    "春运",
    "客运",
    "民生",
    "社会治理",
    "公共安全"
]

# 七、权威来源
AUTHORITATIVE_SOURCES = [
    "财联社",
    "证券时报",
    "人民财讯",
    "公司公告",
    "交易所公告",
    "巨潮资讯",
    "上交所",
    "深交所",
    "北交所",
    "cls"  # 财联社英文标识
]


# ============================================================
# 华尔街见闻新闻关键词
# ============================================================

# 华尔街见闻高价值关键词
WALLSTREETCN_HIGH_VALUE_KEYWORDS = [
    "美联储", "鲍威尔", "降息", "加息", "利率决议", "点阵图",
    "CPI", "PCE", "非农", "初请失业金", "零售销售", "PMI",
    "美元", "美债", "收益率", "10年期美债", "2年期美债",
    "黄金", "原油", "OPEC", "EIA", "API",
    "纳指", "标普", "道指", "VIX", "恐慌指数",
    "英伟达", "特斯拉", "苹果", "微软", "Meta", "谷歌",
    "台积电", "ASML", "美光", "博通", "AMD",
    "半导体", "AI", "算力", "芯片", "服务器", "数据中心",
    "港股科技", "中概股", "人民币汇率"
]

# 华尔街见闻低价值关键词
WALLSTREETCN_LOW_VALUE_KEYWORDS = [
    "直播",
    "专栏",
    "会员",
    "广告",
    "活动",
    "课程",
    "招聘"
]


# ============================================================
# 新增：CLS 新闻规则增强
# ============================================================

# 股票代码正则模式
STOCK_CODE_PATTERN = re.compile(
    r'([一-龥A-Za-z0-9·]{2,20})'  # 公司名
    r'[（(]'  # 左括号（中英文）
    r'(\d{6}(?:\.(SH|SZ|BJ|HK))?|'  # A股代码（可选后缀）
    r'\d{5}\.HK|'  # 港股
    r'[A-Z]{1,5}(?:\.US)?)'  # 美股
    r'[）)]'  # 右括号（中英文）
)

# 海外 AI 基建关键词
AI_INFRA_KEYWORDS = [
    "AI工厂", "AI factory", "人工智能工厂",
    "AI基础设施", "AI infrastructure",
    "数据中心", "data center", "数据中心园区", "扩建数据中心",
    "cloud infrastructure", "云基础设施",
    "算力基础设施", "AI算力",
    "GPU集群", "GPU cluster",
    "加速计算", "accelerated computing",
    # 企业AI
    "代理式人工智能", "代理式AI", "agentic AI",
    "引入生产环境", "生产环境", "enterprise AI",
]

# 海外 AI 公司关键词
OVERSEAS_AI_COMPANIES = [
    "英伟达", "NVIDIA",
    "谷歌", "Google",
    "OpenAI",
    "微软", "Microsoft",
    "亚马逊", "AWS",
    "Meta",
    "Equinix",
    "思科", "Cisco",
    "Oracle",
    "CoreWeave",
    # 新增
    "慧与科技", "HPE", "惠普企业",
    "甲骨文",
]

# AI 软件/Copilot关键词
AI_SOFTWARE_KEYWORDS = [
    "Copilot", "copilot",
    "DeepSeek", "deepseek",
    "协同工作平台", "协作功能", "协作平台",
    "AI助手", "agent",
    "Microsoft 365", "Office AI",
    "AI办公", "productivity AI",
]

# 液冷关键词
LIQUID_COOLING_KEYWORDS = [
    "液冷", "liquid cooling",
    "Brazos液冷系统", "brazos",
    "数据中心冷却", "cooling system",
    "thermal management", "散热系统",
]

# 动作关键词
AI_INFRA_INVESTMENT_KEYWORDS = ["投资", "扩建", "建设", "资本开支", "capex", "建厂"]
AI_INFRA_COOPERATION_KEYWORDS = ["携手", "合作", "部署"]
AI_INFRA_FINANCING_KEYWORDS = ["发债", "筹资", "融资", "债券"]
AI_INFRA_ORDER_KEYWORDS = ["订单", "采购"]

# 战争/地缘冲突关键词
WAR_KEYWORDS = [
    "俄", "俄罗斯", "乌克兰", "乌军", "俄军", "白俄罗斯",
    "伊朗", "以色列",
    "恐袭", "袭击", "打击",
    "导弹", "拦截", "空袭", "战斗",
    "军方", "炼油厂", "防空系统",
    "战争", "停火",
    "霍尔木兹", "真主党", "核谈判",
    "攻击型无人机", "固定翼无人机",
]

# 能源关键词
ENERGY_KEYWORDS = [
    "炼油厂", "原油", "油轮", "港口", "霍尔木兹",
    "油价", "LPG", "成品油", "天然气", "化学品", "甲醇"
]


def extract_stocks_by_code_pattern(text: str) -> list[dict]:
    """
    硬解析股票代码（规则层提取）

    识别格式：
    - 复星医药(600196.SH)
    - 粤万年青(301111.SZ)
    - 复星医药（600196）  # 中文括号
    - 腾讯控股(00700.HK)
    - NVIDIA(NVDA.US)

    Args:
        text: 待匹配文本

    Returns:
        提取到的股票列表
    """
    matches = STOCK_CODE_PATTERN.findall(text)
    stocks = []
    seen_codes = set()

    for name, code, exchange in matches:
        # 补全交易所后缀
        if '.' not in code:
            if code.startswith('6'):
                code = f"{code}.SH"
            elif code.startswith(('0', '3')):
                code = f"{code}.SZ"
            elif code.startswith(('8', '4')):
                code = f"{code}.BJ"

        # 去重
        if code in seen_codes:
            continue
        seen_codes.add(code)

        stocks.append({
            "code": code,
            "name": name.strip(),
            "market": "A股" if code.endswith(('.SH', '.SZ', '.BJ')) else "港股" if '.HK' in code else "美股",
            "match_type": "name_code_pattern",
            "confidence": 1.0
        })

    return stocks


def classify_overseas_ai_infrastructure(item: dict) -> Optional[dict]:
    """
    海外 AI 基建/软件/产品主题分类

    支持三类：
    A. AI 基础设施/企业AI合作
    B. AI 软件（Copilot/DeepSeek）
    C. 液冷系统

    Returns:
        分类结果 dict 或 None
    """
    # 构建完整文本
    title = item.get('title', '')
    content = item.get('content', '')
    normalized_title = item.get('normalized_title', '')
    text = f"{normalized_title} {title} {content}".lower()

    # === A. AI 软件（Copilot/DeepSeek）优先级最高 ===
    if any(kw.lower() in text for kw in AI_SOFTWARE_KEYWORDS):
        # 检查是否有公司关键词
        if any(kw.lower() in text for kw in OVERSEAS_AI_COMPANIES):
            return {
                "event_type": "ai_product_update",
                "primary_theme_id": "ai_software",
                "primary_theme_name": "AI软件",
                "trade_priority": "watch",
                "final_score": 55,
                "confidence": 0.75,
                "ai_level": "light"
            }

    # === B. 液冷系统 ===
    if any(kw.lower() in text for kw in LIQUID_COOLING_KEYWORDS):
        # 同时命中数据中心
        if '数据中心' in text or 'data center' in text:
            result = {
                "event_type": "ai_infrastructure_product",
                "primary_theme_id": "ai_compute",
                "primary_theme_name": "AI算力",
                "trade_priority": "candidate",
                "final_score": 65,
                "confidence": 0.8,
                "ai_level": "light"
            }
            # 添加液冷主题
            theme_ids = item.get('theme_ids', [])
            theme_names = item.get('theme_names', [])
            if 'liquid_cooling' not in theme_ids:
                theme_ids.append('liquid_cooling')
                theme_names.append('液冷')
            result['theme_ids'] = theme_ids
            result['theme_names'] = theme_names
            return result

    # === C. AI 基础设施/企业AI ===
    # 检查 AI 基建关键词
    if not any(kw.lower() in text for kw in AI_INFRA_KEYWORDS):
        return None

    # 检查海外公司关键词
    if not any(kw.lower() in text for kw in OVERSEAS_AI_COMPANIES):
        return None

    # 判断动作类型（发债优先级最高，避免被投资关键词覆盖）
    if any(kw in text for kw in AI_INFRA_FINANCING_KEYWORDS):
        return {
            "event_type": "financing_for_ai_capex",
            "primary_theme_id": "ai_compute",
            "primary_theme_name": "AI算力",
            "trade_priority": "watch",
            "final_score": 50,
            "confidence": 0.7,
            "ai_level": "light"
        }

    if any(kw in text for kw in AI_INFRA_ORDER_KEYWORDS):
        return {
            "event_type": "order_win",
            "primary_theme_id": "ai_compute",
            "primary_theme_name": "AI算力",
            "trade_priority": "candidate",
            "final_score": 70,
            "confidence": 0.8,
            "ai_level": "deep"
        }

    if any(kw in text for kw in AI_INFRA_INVESTMENT_KEYWORDS):
        return {
            "event_type": "ai_infrastructure_investment",
            "primary_theme_id": "ai_compute",
            "primary_theme_name": "AI算力",
            "trade_priority": "candidate",
            "final_score": 65,
            "confidence": 0.8,
            "ai_level": "light"
        }

    if any(kw in text for kw in AI_INFRA_COOPERATION_KEYWORDS):
        # 判断是否企业AI合作
        if any(kw in text for kw in ['代理式', 'agentic', '生产环境', 'enterprise']):
            return {
                "event_type": "enterprise_ai_cooperation",
                "primary_theme_id": "ai_compute",
                "primary_theme_name": "AI算力",
                "trade_priority": "watch",
                "final_score": 55,
                "confidence": 0.75,
                "ai_level": "light"
            }
        else:
            return {
                "event_type": "strategic_cooperation",
                "primary_theme_id": "ai_compute",
                "primary_theme_name": "AI算力",
                "trade_priority": "candidate",
                "final_score": 65,
                "confidence": 0.8,
                "ai_level": "light"
            }

    return None


def fix_war_drone_theme(item: dict) -> dict:
    """
    战争无人机主题修正

    如果：
    1. primary_theme_id == "low_altitude_economy"
    2. 文本包含"无人机"
    3. 文本包含战争关键词

    则修正为 geopolitical_risk
    """
    # 检查是否需要修正
    if item.get('primary_theme_id') != 'low_altitude_economy':
        return item

    # 构建完整文本
    title = item.get('title', '')
    content = item.get('content', '')
    normalized_title = item.get('normalized_title', '')
    text = f"{normalized_title} {title} {content}"

    # 检查无人机关键词
    if '无人机' not in text and 'drone' not in text.lower() and 'uav' not in text.lower():
        return item

    # 检查战争关键词
    if not any(kw in text for kw in WAR_KEYWORDS):
        return item

    # 修正主题
    item['event_type'] = 'geopolitical_risk'
    item['trade_priority'] = 'watch'
    item['final_score'] = 40
    item['ai_level'] = 'none'
    item['need_ai'] = False

    # 判断是否涉及能源
    if any(kw in text for kw in ENERGY_KEYWORDS):
        item['primary_theme_id'] = 'energy_risk'
        item['primary_theme_name'] = '能源风险'
    else:
        item['primary_theme_id'] = None
        item['primary_theme_name'] = None

    # 添加风险标记
    risk_flags = item.get('risk_flags', [])
    if 'geopolitical_conflict' not in risk_flags:
        risk_flags.append('geopolitical_conflict')
    if 'war_drone_not_low_altitude' not in risk_flags:
        risk_flags.append('war_drone_not_low_altitude')
    item['risk_flags'] = risk_flags

    return item


def apply_ai_level(item: dict) -> dict:
    """
    计算 ai_level 并兼容 need_ai

    ai_level 可选：
    - none: 不需要AI处理
    - light: 轻量AI处理
    - deep: 深度AI处理
    - urgent: 紧急AI处理

    Args:
        item: 新闻 item

    Returns:
        增强后的 item
    """
    # 如果已经设置了 ai_level，保持不变
    if item.get('ai_level') and item['ai_level'] != 'none':
        item['need_ai'] = item['ai_level'] in ['light', 'deep', 'urgent']
        return item

    event_type = item.get('event_type', '')
    final_score = item.get('final_score', 0)
    related_stocks_count = item.get('related_stocks_count', 0)
    primary_theme_id = item.get('primary_theme_id', '')
    risk_flags = item.get('risk_flags', [])

    # 构建文本用于关键词检测
    title = item.get('title', '')
    content = item.get('content', '')
    normalized_title = item.get('normalized_title', '')
    text = f"{normalized_title} {title} {content}".lower()

    # 1. 付费研报标题
    if event_type == 'paid_research_teaser':
        ai_level = 'light'

    # 2. 战争无人机
    elif 'war_drone_not_low_altitude' in risk_flags:
        ai_level = 'none'

    # 3. 强催化剂
    elif event_type in [
        'order_win', 'capacity_expansion', 'product_launch',
        'strategic_cooperation', 'merger_acquisition'
    ]:
        ai_level = 'deep'

    # 4. 海外 AI 基建但没有 A股个股
    elif event_type in [
        'ai_infrastructure_investment', 'strategic_cooperation',
        'financing_for_ai_capex', 'enterprise_ai_cooperation',
        'ai_product_update', 'ai_terminal_product'
    ] and related_stocks_count == 0:
        ai_level = 'light'

    # 5. 明确上市公司公告且有股票代码
    elif related_stocks_count > 0:
        if final_score >= 60:
            ai_level = 'deep'
        else:
            ai_level = 'light'

    # 6. general + 低分 + 无题材 + 无股票
    elif event_type == 'general' and final_score < 50 and not primary_theme_id and related_stocks_count == 0:
        # 检查是否命中强AI/半导体/算力关键词
        strong_ai_keywords = [
            '英伟达', 'nvidia', 'openai', '谷歌', 'google',
            '微软', 'microsoft', 'deepseek', 'copilot',
            '数据中心', 'ai工厂', '液冷', '算力',
            'gpu', '半导体', '光模块', 'hbm'
        ]

        if any(kw in text for kw in strong_ai_keywords):
            # 有AI关键词，给light级别，但分数至少45
            ai_level = 'light'
            if final_score < 45:
                item['final_score'] = 45
            if not item.get('trade_priority'):
                item['trade_priority'] = 'watch'
        else:
            # 纯general低分，archive
            ai_level = 'none'
            if not item.get('trade_priority'):
                item['trade_priority'] = 'archive'

    # 7. 新闻联播、宏观数据、期货收盘
    elif event_type in ['macro_data', 'market_close', 'government_meeting']:
        ai_level = 'none'

    # 8. 地缘风险
    elif event_type == 'geopolitical_risk':
        ai_level = 'none'

    # 9. 默认规则
    else:
        if final_score >= 65:
            ai_level = 'deep'
        elif final_score >= 50:
            ai_level = 'light'
        else:
            ai_level = 'none'

    item['ai_level'] = ai_level
    item['need_ai'] = ai_level in ['light', 'deep', 'urgent']

    return item


def classify_apple_ai_terminal(item: dict) -> Optional[dict]:
    """
    苹果 AI 终端/可穿戴/折叠屏主题分类

    识别：
    - AirPods（尤其是带摄像头）
    - 折叠iPhone
    - AI可穿戴设备

    映射到 consumer_electronics / ai_terminal，而不是 semiconductor_material

    Returns:
        分类结果 dict 或 None
    """
    # 构建完整文本
    title = item.get('title', '')
    content = item.get('content', '')
    normalized_title = item.get('normalized_title', '')
    text = f"{normalized_title} {title} {content}".lower()

    # 必须命中苹果
    if not any(kw in text for kw in ['苹果', 'apple', 'iphone', 'airpods']):
        return None

    # AI终端/可穿戴关键词
    ai_terminal_keywords = [
        'airpods', '摄像头airpods', 'ai可穿戴', '可穿戴设备',
        'siri', '计算机视觉', '视觉传感', 'camera sensor',
    ]

    # 折叠屏关键词
    foldable_keywords = [
        '折叠iphone', '折叠手机', 'foldable iphone', 'foldable phone', '折叠屏'
    ]

    # 检查是否命中
    is_ai_terminal = any(kw in text for kw in ai_terminal_keywords)
    is_foldable = any(kw in text for kw in foldable_keywords)

    if not (is_ai_terminal or is_foldable):
        return None

    # 构建主题
    theme_ids = ['consumer_electronics']
    theme_names = ['消费电子']

    if is_ai_terminal:
        theme_ids.extend(['ai_terminal', 'ai_wearable'])
        theme_names.extend(['AI终端', 'AI可穿戴'])

    if is_foldable:
        if 'foldable_phone' not in theme_ids:
            theme_ids.append('foldable_phone')
            theme_names.append('折叠屏')

    return {
        "event_type": "ai_terminal_product",
        "primary_theme_id": "consumer_electronics",
        "primary_theme_name": "消费电子",
        "theme_ids": theme_ids,
        "theme_names": theme_names,
        "trade_priority": "candidate",
        "final_score": 65,
        "confidence": 0.75,
        "ai_level": "light"
    }


# ============================================================
# 华尔街见闻市场上下文分类
# ============================================================

def build_normalized_title(title: str, content: str, max_len: int = 80) -> str:
    """
    构建标准化标题

    Args:
        title: 原始标题
        content: 正文内容
        max_len: 最大长度

    Returns:
        标准化标题
    """
    if title and title.strip():
        # 清洗标题
        normalized = title.strip()
    else:
        # 从正文生成
        normalized = content.strip()

        # 去除前缀
        prefixes = [
            '财联社',
            '华尔街见闻',
            '见闻注',
        ]
        for prefix in prefixes:
            if prefix in normalized:
                # 尝试找到第一个句号或逗号后的内容
                import re
                match = re.search(rf'{prefix}.*?[，。：](.+)', normalized)
                if match:
                    normalized = match.group(1).strip()
                    break

    # 去除多余空白
    import re
    normalized = re.sub(r'\s+', ' ', normalized)

    # 截取
    if len(normalized) > max_len:
        normalized = normalized[:max_len]

    # 确保非空
    if not normalized:
        normalized = content[:max_len] if content else "无标题"

    return normalized


def classify_wallstreetcn_market_context(item: dict) -> dict:
    """
    华尔街见闻市场上下文分类

    不同于CLS题材事件源，wallstreetcn定位为市场环境判断

    Args:
        item: 新闻item

    Returns:
        分类结果
    """
    title = item.get('title', '')
    content = item.get('content', '')
    normalized_title = item.get('normalized_title', '')

    # 构建完整文本
    text = f"{normalized_title} {title} {content}".lower()

    # 默认结果
    result = {
        'source_role': 'market_context',
        'context_type': 'low_value',
        'impact_assets': [],
        'market_bias': 'neutral',
        'importance': 'low',
        'ai_level': 'none',
        'need_ai': False,
        'reason': '',
        'theme_hint_ids': [],
        'theme_hint_names': [],
    }

    # 1. 宏观数据
    macro_keywords = ['cpi', 'ppi', '非农', '初请', '零售销售', '商业库存', '成屋签约',
                      'ism', 'pmi', '消费者信心', '密歇根', '纽约联储', '费城联储',
                      'gdp', 'pce', '核心pce']

    if any(kw in text for kw in macro_keywords):
        result['context_type'] = 'macro_data'
        result['impact_assets'] = ['US10Y', 'USD', 'QQQ']

        # 高优先级数据
        high_priority = ['cpi', '核心cpi', 'pce', '核心pce', '非农', '失业率',
                         '初请失业金', '零售销售', 'fomc', '利率决议']
        if any(kw in text for kw in high_priority):
            result['importance'] = 'high'
            result['ai_level'] = 'light'
            result['need_ai'] = True
            result['reason'] = '重要宏观数据将影响利率预期和市场风险偏好'
        else:
            result['reason'] = '常规宏观数据'

        return result

    # 2. 美联储/利率政策
    fed_keywords = ['美联储', 'fomc', '点阵图', 'sep', '利率决议', '降息', '加息',
                    '沃什', '鲍威尔', '美联储主席', '鹰派', '鸽派',
                    '通胀', '抗击通胀', '联邦基金', 'sofr', 'rrp', '逆回购',
                    '美债收益率', '债市波动', '短端美债', '长端曲线', '收益率曲线',
                    '联邦基金期货', '交易员加码押注', '政策决定']

    if any(kw in text for kw in fed_keywords):
        result['context_type'] = 'fed_policy'
        result['impact_assets'] = ['US10Y', 'US2Y', 'TLT', 'USD', 'QQQ', 'SMH', 'GOLD']

        # RRP/SOFR日常数据
        if any(kw in text for kw in ['sofr', 'rrp', '逆回购']) and not any(kw in text for kw in ['决议', '点阵图', '鲍威尔', '沃什', '波动']):
            result['importance'] = 'low'
            result['reason'] = '日常流动性数据'
        else:
            # 判断重要性
            high_priority_signals = ['决议', '点阵图', '鲍威尔']
            waller_volatility = '沃什' in text and any(kw in text for kw in ['波动', '美债', '收益率', '曲线', '鹰派', '加息', '立场'])

            if any(kw in text for kw in high_priority_signals) or waller_volatility:
                result['importance'] = 'high'
            else:
                result['importance'] = 'medium'

            result['ai_level'] = 'light'
            result['need_ai'] = True

            # 判断市场偏好（增强沃什/波动性判断）
            # 沃什+波动/立场暗示鹰派
            waller_hawkish = '沃什' in text and any(kw in text for kw in ['波动', '立场', '短端'])

            if any(kw in text for kw in ['鹰派', '加息', '抗击通胀']) or ('收益率' in text and '上行' in text) or waller_hawkish:
                result['market_bias'] = 'risk_off'
                result['reason'] = 'FOMC决议和点阵图将影响利率、美元和成长股估值' if '决议' in text or '点阵图' in text else '美联储鹰派信号推升加息预期，压制成长股估值'
            elif any(kw in text for kw in ['鸽派', '降息']) or ('收益率' in text and '下行' in text):
                result['market_bias'] = 'risk_on'
                result['reason'] = '美联储鸽派信号缓解加息压力，利好成长股估值'
            else:
                result['market_bias'] = 'neutral'
                result['reason'] = '美联储政策信号将影响市场预期'

        return result

    # 3. 市场行情异动
    market_keywords = ['纳指', '标普500', '道指', '半导体etf', '费城半导体', '科技股指数',
                       'spacex', '美股盘初', '美股盘前', '高开', '低开', '收涨', '收跌',
                       '涨幅扩大', '跌幅扩大']

    if any(kw in text for kw in market_keywords):
        result['context_type'] = 'market_move'

        # 判断资产
        if '半导体' in text or '费城半导体' in text:
            result['impact_assets'] = ['SMH', 'SOXX', 'NVDA', 'AMD']
            result['theme_hint_ids'] = ['semiconductor']
            result['theme_hint_names'] = ['半导体']
        elif 'spacex' in text:
            result['impact_assets'] = ['SPACE_THEME', 'SATELLITE', 'RKLB']
        else:
            result['impact_assets'] = ['QQQ', 'NASDAQ']

        # 判断市场偏好（修复：优先判断"转跌"等明确信号）
        if any(kw in text for kw in ['转跌', '跌', '下跌', '跌幅扩大', '低开']):
            result['market_bias'] = 'risk_off'
        elif any(kw in text for kw in ['涨', '高开', '涨幅扩大', '上涨']):
            result['market_bias'] = 'risk_on'
        else:
            result['market_bias'] = 'mixed'

        # 判断重要性
        import re
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        if percentages:
            max_pct = max(float(p) for p in percentages)
            if '半导体' in text and max_pct >= 3:
                result['importance'] = 'medium'
                result['ai_level'] = 'light'
                result['need_ai'] = True
                result['reason'] = '半导体板块大幅波动将影响科技股和A股芯片产业链'
            elif '纳指' in text and max_pct >= 1.5:
                result['importance'] = 'medium'
                result['ai_level'] = 'light'
                result['need_ai'] = True
                result['reason'] = '纳指大幅波动将影响全球科技股风险偏好'
            elif 'spacex' in text and max_pct >= 10:
                result['importance'] = 'medium'
                result['ai_level'] = 'light'
                result['need_ai'] = True
                result['reason'] = 'SpaceX大幅波动将影响卫星产业链和商业航天主题'

        if not result['reason']:
            result['reason'] = '市场行情日常波动'

        return result

    # 4. 商品/油价
    commodity_keywords = ['wti', '布伦特', '原油', '油价', '天然气', '黄金', '白银',
                         '铜', '铝', 'lme', '大豆', '小麦', '玉米']

    if any(kw in text for kw in commodity_keywords):
        result['context_type'] = 'commodity_move'

        # 判断资产
        if any(kw in text for kw in ['原油', 'wti', '布伦特', '油价']):
            result['impact_assets'] = ['WTI', 'Brent', 'XLE', '油气', '航运']
        elif any(kw in text for kw in ['黄金', '白银']):
            result['impact_assets'] = ['GOLD', 'GLD', '贵金属']
        elif any(kw in text for kw in ['铜', '铝', 'lme']):
            result['impact_assets'] = ['工业金属', '有色金属']

        # 判断重要性
        import re
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        if percentages:
            max_pct = max(float(p) for p in percentages)
            if max_pct >= 5:
                result['importance'] = 'high'
                result['ai_level'] = 'light'
                result['need_ai'] = True
                result['reason'] = '大宗商品大幅波动将影响通胀预期和相关产业链'
            elif max_pct >= 2:
                result['importance'] = 'medium'
                result['ai_level'] = 'light'
                result['need_ai'] = True
                result['reason'] = '商品价格中等波动将影响相关板块'

        # 判断市场偏好
        if any(kw in text for kw in ['原油', '油价']) and any(kw in text for kw in ['涨', '上涨']):
            result['market_bias'] = 'mixed'
        elif any(kw in text for kw in ['原油', '油价']) and any(kw in text for kw in ['跌', '下跌']):
            result['market_bias'] = 'risk_on'

        if not result['reason']:
            result['reason'] = '商品价格常规波动'

        return result

    # 5. 地缘能源风险
    # 强市场影响
    geopolitical_energy_keywords = ['霍尔木兹', '油轮', '港口封锁', '原油出口', '石油出口',
                                     '炼油厂', '美军介入', '空袭伊朗', '核设施', '制裁升级',
                                     '航运中断', '中东战争升级', '扫雷']

    # 弱市场影响
    geopolitical_weak_keywords = ['谴责', '声明', '呼吁', '定居者', '清真寺', '宗教场所']

    # 基础地缘关键词
    geopolitical_base_keywords = ['伊朗', '以色列', '俄罗斯', '乌克兰', '真主党',
                                   '停火', '谅解备忘录', '导弹', '空袭', '制裁', 'g7', '普京', '泽连斯基']

    # 特朗普/默茨单独处理：需要配合地缘关键词
    trump_geopolitical = '特朗普' in text and any(kw in text for kw in ['霍尔木兹', '伊朗', '以色列', '俄罗斯', '乌克兰', '导弹', '制裁', '停火'])
    merz_geopolitical = '默茨' in text and any(kw in text for kw in ['霍尔木兹', '扫雷'])

    has_geopolitical = any(kw in text for kw in geopolitical_base_keywords) or trump_geopolitical or merz_geopolitical
    has_strong_impact = any(kw in text for kw in geopolitical_energy_keywords)
    has_weak_signal = any(kw in text for kw in geopolitical_weak_keywords)

    if has_geopolitical:
        # 强市场影响 - 地缘能源
        if has_strong_impact:
            result['context_type'] = 'geopolitical_energy'
            result['impact_assets'] = ['WTI', 'Brent', 'GOLD', 'USD', '航运', '油气']
            result['importance'] = 'high' if '霍尔木兹' in text or '核设施' in text else 'medium'
            result['ai_level'] = 'light'
            result['need_ai'] = True

            # 判断市场偏好
            if any(kw in text for kw in ['停火', '开放', '协议签署', '谅解备忘录']):
                result['market_bias'] = 'risk_on'
                result['reason'] = '地缘风险缓和将降低能源溢价和避险情绪'
            elif any(kw in text for kw in ['空袭', '制裁', '封锁', '核设施']):
                result['market_bias'] = 'risk_off'
                result['reason'] = '地缘风险升级将推升油价和避险资产'
            else:
                result['reason'] = '地缘政治动态将影响能源和避险资产'

            return result

        # 弱市场影响 - 普通地缘
        elif has_weak_signal or any(kw in text for kw in ['讲话', '表示', '称', '认为']):
            result['context_type'] = 'geopolitical'
            result['impact_assets'] = ['GOLD']
            result['market_bias'] = 'risk_off'
            result['importance'] = 'low'
            result['ai_level'] = 'none'
            result['need_ai'] = False
            result['reason'] = '普通地缘/外交表态，对主要交易资产影响有限'

            return result

        # 中等影响 - 有实质动作但非能源核心
        else:
            result['context_type'] = 'geopolitical_energy'
            result['impact_assets'] = ['WTI', 'Brent', 'GOLD', 'USD', '航运', '油气']
            result['importance'] = 'medium'
            result['ai_level'] = 'light'
            result['need_ai'] = True

            # 判断市场偏好
            if any(kw in text for kw in ['停火', '开放', '协议签署']):
                result['market_bias'] = 'risk_on'
                result['reason'] = '地缘风险缓和将降低能源溢价和避险情绪'
            else:
                result['market_bias'] = 'risk_off'
                result['reason'] = '地缘政治动态将影响能源和避险资产'

            return result

    # 6. 中国资产/港股政策
    china_keywords = ['陆家嘴论坛', '港交所', '港股ipo', '再融资', '人民币国债期货',
                     '港股通', '南向资金', '外资看好中国', '中国市场兴趣升温',
                     '人民币股票交易', '香港证监会', '沪港金融', '债券通', '南向通', '黄金交易中心']

    if any(kw in text for kw in china_keywords):
        result['context_type'] = 'china_market_policy'
        result['impact_assets'] = ['恒生科技', '港股', 'A股金融', '券商', '中国资产']
        result['market_bias'] = 'risk_on'
        result['importance'] = 'medium'
        result['ai_level'] = 'light'
        result['need_ai'] = True
        result['reason'] = '中国资产政策利好将提升港股和A股金融板块吸引力'

        # 普通会议表述
        if any(kw in text for kw in ['表示', '称', '认为']) and not any(kw in text for kw in ['ipo', '再融资', '兴趣升温', '看好']):
            result['importance'] = 'low'
            result['ai_level'] = 'none'
            result['need_ai'] = False
            result['reason'] = '普通会议表述'

        return result

    # 7. 美股科技/风险偏好
    us_equity_keywords = ['半导体etf', '费城半导体', '科技股', 'spacex', 'ai', '人工智能',
                         'cme', 'nvda', 'amd', 'arm', '美光', '阿斯麦', '博通', '纳指',
                         '英伟达', '亚马逊', '谷歌', '微软', 'meta', '苹果',
                         'trainium', 'ai芯片', '自研芯片', 'ai算力', '云计算']

    if any(kw in text for kw in us_equity_keywords):
        result['context_type'] = 'us_equity_sentiment'
        result['impact_assets'] = ['QQQ', 'SMH', 'SOXX', 'NVDA', 'AMD']

        # AI芯片/算力相关
        if any(kw in text for kw in ['ai芯片', '自研芯片', 'trainium', 'ai算力', '英伟达', 'nvda']):
            if 'amzn' in text or '亚马逊' in text:
                result['impact_assets'] = ['AMZN', 'NVDA', 'SMH', 'AI算力']
            result['theme_hint_ids'] = ['ai_compute', 'ai_chip']
            result['theme_hint_names'] = ['AI算力', 'AI芯片']

            # 竞品芯片新闻
            if any(kw in text for kw in ['竞品', '自研', 'trainium']) and ('nvda' in text or '英伟达' in text):
                result['market_bias'] = 'mixed'
                result['reason'] = '亚马逊自研AI芯片商业化可能强化AI芯片竞争格局，利好AMZN自研芯片叙事但压制NVDA垄断溢价'
                result['importance'] = 'medium'
                result['ai_level'] = 'light'
                result['need_ai'] = True
                return result

        # 判断市场偏好
        if any(kw in text for kw in ['转跌', '跌', '下跌', '跌幅扩大']):
            result['market_bias'] = 'risk_off'
        elif any(kw in text for kw in ['涨', '高开', '涨幅扩大', '上涨']):
            result['market_bias'] = 'risk_on'

        # 判断重要性
        import re
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        if percentages:
            max_pct = max(float(p) for p in percentages)
            if max_pct >= 3:
                result['importance'] = 'medium'
                result['ai_level'] = 'light'
                result['need_ai'] = True
                result['reason'] = '半导体板块大幅波动将影响全球芯片产业链'
            else:
                result['reason'] = '科技股日常波动'
        else:
            result['reason'] = '科技股动态'

        if '半导体' in text:
            result['theme_hint_ids'] = ['semiconductor']
            result['theme_hint_names'] = ['半导体']

        return result

    # 8. 科技突破
    tech_keywords = ['成功攻克', '国产', '技术突破', '首款', '顺利出炉', '高强度钢',
                    '极地钢', '6g', 'mrna', 'crispr', 'ai驱动']

    if any(kw in text for kw in tech_keywords):
        result['context_type'] = 'technology_breakthrough'
        result['impact_assets'] = ['新材料', '高端装备']
        result['market_bias'] = 'neutral'
        result['importance'] = 'low'
        result['reason'] = '技术突破，但无明确交易映射'

        # 如果有明确A股映射
        if any(kw in text for kw in ['上市公司', 'a股', '沪深']):
            result['importance'] = 'medium'
            result['ai_level'] = 'light'
            result['need_ai'] = True
            result['reason'] = '技术突破可能影响相关A股公司'

        return result

    # 9. 默认低价值
    result['context_type'] = 'low_value'
    result['reason'] = '普通资讯'

    return result


# ============================================================
# CLS 题材关键词补充（HBM、MLCC、CPO、液冷、PCB、算力租赁）
# ============================================================

# HBM / 存储芯片
HBM_KEYWORDS = [
    'hbm', 'hbm4', 'hbm4e', '高带宽内存',
    'dram', '存储芯片', 'sk海力士', '三星电子', '美光',
]

# MLCC / 被动元件
MLCC_KEYWORDS = [
    'mlcc', '多层陶瓷电容', '铝电解电容',
    '尼吉康', '村田', '太阳诱电', 'tdk',
    '芯片电感', '电感', '被动元件',
    '陶瓷粉体', '瓷粉材料',
]

# CPO / 光模块
CPO_KEYWORDS = [
    'cpo', '光模块', '光通信', '光芯片', '光耦合', '硅光',
    '800g', '1.6t', '中际旭创', '新易盛', '光迅科技', '天孚通信',
]

# 液冷 / AI服务器
LIQUID_COOLING_KEYWORDS = [
    '液冷', '直接芯片液冷', '冷板', '浸没式液冷',
    'ai服务器', '数据中心散热', '高密度计算',
]

# PCB
PCB_KEYWORDS = [
    'pcb', '高速pcb', 'msap', 'abf',
    '覆铜板', '玻纤布', '电子布', '高速覆铜板',
]

# 算力租赁
AI_COMPUTE_RENTAL_KEYWORDS = [
    '算力租赁', '算力基础设施', '算力并网', '算力池化',
    '分布式算力', 'b200租赁', 'gpu租赁', '推理基础设施',
]


def classify_theme_by_keywords(title: str, content: str) -> dict:
    """
    根据关键词补充题材分类

    Args:
        title: 标题
        content: 正文

    Returns:
        题材信息 {primary_theme_id, primary_theme_name, related_etfs}
    """
    text = (title + " " + content).lower()

    # HBM / 存储芯片
    if any(kw in text for kw in HBM_KEYWORDS):
        return {
            'primary_theme_id': 'memory_chip',
            'primary_theme_name': 'HBM/存储芯片',
            'related_etfs': ['159516.SZ', '516350.SH'],
        }

    # MLCC / 被动元件
    if any(kw in text for kw in MLCC_KEYWORDS):
        return {
            'primary_theme_id': 'passive_components',
            'primary_theme_name': '被动元件',
            'related_etfs': [],
        }

    # CPO / 光模块
    if any(kw in text for kw in CPO_KEYWORDS):
        return {
            'primary_theme_id': 'optical_module',
            'primary_theme_name': '光模块/CPO',
            'related_etfs': [],
        }

    # 液冷
    if any(kw in text for kw in LIQUID_COOLING_KEYWORDS):
        return {
            'primary_theme_id': 'liquid_cooling',
            'primary_theme_name': '液冷服务器',
            'related_etfs': [],
        }

    # PCB
    if any(kw in text for kw in PCB_KEYWORDS):
        return {
            'primary_theme_id': 'pcb',
            'primary_theme_name': 'PCB',
            'related_etfs': [],
        }

    # 算力租赁
    if any(kw in text for kw in AI_COMPUTE_RENTAL_KEYWORDS):
        return {
            'primary_theme_id': 'ai_compute',
            'primary_theme_name': 'AI算力',
            'related_etfs': [],
        }

    return {}


__all__ = [
    'RISK_KEYWORDS',
    'RISK_KEYWORD_TO_FLAG',
    'STRONG_EVENT_KEYWORDS',
    'CANDIDATE_KEYWORDS',
    'STRONG_ENTITY_KEYWORDS',
    'LOW_VALUE_KEYWORDS',
    'JUNK_KEYWORDS',
    'MACRO_FINANCE_KEYWORDS',
    'OVERSEAS_MARKET_KEYWORDS',
    'GEOPOLITICS_KEYWORDS',
    'MARKET_DATA_KEYWORDS',
    'EXEC_NORMAL_CHANGE_KEYWORDS',
    'SOCIAL_GOVERNANCE_KEYWORDS',
    'AUTHORITATIVE_SOURCES',
    'BUSINESS_METRIC_KEYWORDS',
    'TECH_BREAKTHROUGH_CONTEXT',
    # 华尔街见闻
    'WALLSTREETCN_HIGH_VALUE_KEYWORDS',
    'WALLSTREETCN_LOW_VALUE_KEYWORDS',
    'build_normalized_title',
    'classify_wallstreetcn_market_context',
    # CLS增强
    'extract_stocks_by_code_pattern',
    'classify_overseas_ai_infrastructure',
    'classify_apple_ai_terminal',
    'fix_war_drone_theme',
    'apply_ai_level',
    'STOCK_CODE_PATTERN',
    'AI_INFRA_KEYWORDS',
    'AI_SOFTWARE_KEYWORDS',
    'LIQUID_COOLING_KEYWORDS',
    'OVERSEAS_AI_COMPANIES',
    'WAR_KEYWORDS',
    'ENERGY_KEYWORDS',
    # 题材关键词
    'HBM_KEYWORDS',
    'MLCC_KEYWORDS',
    'CPO_KEYWORDS',
    'LIQUID_COOLING_KEYWORDS',
    'PCB_KEYWORDS',
    'AI_COMPUTE_RENTAL_KEYWORDS',
    'classify_theme_by_keywords',
]
