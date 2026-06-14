"""
公告分类规则（优化版）
基于优先级P0-P4分类，解决真实样本中的误判问题
"""

# ============================================================================
# P0: 流程/制度/治理类公告（最高优先级，archive）
# ============================================================================

# 制度类关键词（强匹配，优先级最高）
ROUTINE_GOVERNANCE_KEYWORDS = {
    "管理制度": {"type": "governance_policy_revision", "score": 8},
    "管理办法": {"type": "governance_policy_revision", "score": 8},
    "工作细则": {"type": "governance_policy_revision", "score": 8},
    "实施细则": {"type": "governance_policy_revision", "score": 8},
    "公司章程": {"type": "governance_policy_revision", "score": 5},
    "信息披露管理制度": {"type": "governance_policy_revision", "score": 5},
    "投资者关系管理制度": {"type": "governance_policy_revision", "score": 5},
    "内幕信息知情人登记管理制度": {"type": "governance_policy_revision", "score": 5},
    "募集资金使用管理制度": {"type": "governance_policy_revision", "score": 8},
    "公司债券募集资金管理制度": {"type": "governance_policy_revision", "score": 8},
    "对外投资管理制度": {"type": "governance_policy_revision", "score": 8},
    "对外担保管理制度": {"type": "governance_policy_revision", "score": 8},
    "关联交易管理制度": {"type": "governance_policy_revision", "score": 8},
    "舆情管理制度": {"type": "governance_policy_revision", "score": 5},
    "重大信息内部报告制度": {"type": "governance_policy_revision", "score": 5},
    "董事会秘书工作细则": {"type": "governance_policy_revision", "score": 5},
    "总经理工作细则": {"type": "governance_policy_revision", "score": 5},
    "审计委员会工作细则": {"type": "governance_policy_revision", "score": 5},
    "战略委员会工作细则": {"type": "governance_policy_revision", "score": 5},
    "提名委员会工作细则": {"type": "governance_policy_revision", "score": 5},
    "薪酬与考核委员会工作细则": {"type": "governance_policy_revision", "score": 5},
    "股东会累积投票制实施细则": {"type": "governance_policy_revision", "score": 5},
    "薪酬管理制度": {"type": "compensation_policy", "score": 8},
    "绩效考核制度": {"type": "governance_policy_revision", "score": 5},
}

# 会议/决议/通知类
MEETING_NOTICE_KEYWORDS = {
    "股东会通知": {"type": "shareholder_meeting_notice", "score": 8},
    "股东大会通知": {"type": "shareholder_meeting_notice", "score": 8},
    "召开股东会": {"type": "shareholder_meeting_notice", "score": 8},
    "召开股东大会": {"type": "shareholder_meeting_notice", "score": 8},
    "临时股东会": {"type": "shareholder_meeting_notice", "score": 8},
    "临时股东大会": {"type": "shareholder_meeting_notice", "score": 8},
    "董事会决议": {"type": "board_resolution", "score": 15},
    "监事会决议": {"type": "board_resolution", "score": 15},
    "董事会第": {"type": "board_resolution", "score": 15},  # 匹配"第x届董事会第x次"
    "监事会第": {"type": "board_resolution", "score": 15},
    "业绩说明会": {"type": "earnings_briefing_notice", "score": 12},
}

# 其他低价值治理类
OTHER_ROUTINE_KEYWORDS = {
    # 董责险等
    "董事责任险": {"type": "director_liability_insurance", "score": 10},
    "董监高责任险": {"type": "director_liability_insurance", "score": 10},
    "购买董事、高级管理人员责任险": {"type": "director_liability_insurance", "score": 8},
    "董事、高级管理人员责任险": {"type": "director_liability_insurance", "score": 10},

    # 薪酬方案
    "董事、高级管理人员薪酬方案": {"type": "compensation_policy", "score": 8},
    "董事、高管薪酬方案": {"type": "compensation_policy", "score": 8},
    "薪酬方案": {"type": "compensation_policy", "score": 10},

    # 审计机构
    "聘请2026年度审计机构": {"type": "audit_institution_change", "score": 15},
    "聘请审计机构": {"type": "audit_institution_change", "score": 15},
    "续聘会计师事务所": {"type": "audit_institution_change", "score": 15},
    "聘任会计师事务所": {"type": "audit_institution_change", "score": 15},
    "变更会计师事务所": {"type": "audit_institution_change", "score": 20},

    # 董事候选人
    "提名非独立董事候选人": {"type": "director_candidate_nomination", "score": 15},
    "提名独立董事候选人": {"type": "director_candidate_nomination", "score": 15},
    "董事候选人": {"type": "director_candidate_nomination", "score": 15},
    "监事候选人": {"type": "director_candidate_nomination", "score": 15},

    # 无监管处罚记录声明（新增，避免误报）
    "未被证券监管部门和证券交易所采取监管措施或处罚": {"type": "regulatory_clean_record", "score": 8},
    "未被证券监管部门采取监管措施": {"type": "regulatory_clean_record", "score": 8},
    "未被处罚": {"type": "regulatory_clean_record", "score": 8},
    "最近五年未受到行政处罚": {"type": "regulatory_clean_record", "score": 8},

    # 股权激励调整（新增，避免误报为普通回购）
    "注销部分股票期权": {"type": "equity_incentive_adjustment", "score": 20},
    "回购注销部分限制性股票": {"type": "equity_incentive_adjustment", "score": 20},
    "回购注销限制性股票": {"type": "equity_incentive_adjustment", "score": 20},
    "注销股票期权": {"type": "equity_incentive_adjustment", "score": 20},
    "股权激励计划调整": {"type": "equity_incentive_adjustment", "score": 20},

    # 可转债流程公告（新增）
    "转债摘牌": {"type": "convertible_bond_routine_notice", "score": 15},
    "可转债投资者适当性": {"type": "convertible_bond_routine_notice", "score": 12},
    "转股价格调整提示": {"type": "convertible_bond_routine_notice", "score": 15},

    # 其他
    "独立董事意见": {"type": "board_resolution", "score": 10},
    "法律意见书": {"type": "legal_opinion", "score": 8},
    "审计报告": {"type": "audit_or_verification_report", "score": 10},
    "保荐意见": {"type": "sponsor_opinion", "score": 8},
    "前次募集资金使用情况": {"type": "audit_or_verification_report", "score": 8},
}

# ============================================================================
# P1: 真实风险类公告（risk_review）
# ============================================================================

RISK_KEYWORDS = {
    # 安全事故/停产
    "安全事故": {"type": "safety_accident", "score": 85},
    "发生安全事故": {"type": "safety_accident", "score": 85},
    "生产事故": {"type": "safety_accident", "score": 80},
    "火灾事故": {"type": "safety_accident", "score": 80},
    "爆炸事故": {"type": "safety_accident", "score": 85},
    "停产": {"type": "safety_accident", "score": 75},
    "临时停产": {"type": "safety_accident", "score": 75},
    "人员伤亡": {"type": "safety_accident", "score": 90},

    # 监管/立案/诉讼
    "减持": {"type": "shareholding_reduction", "score": 70},
    "立案": {"type": "case_filing", "score": 85},
    "调查": {"type": "investigation", "score": 80},
    "监管函": {"type": "regulatory_letter", "score": 80},
    "问询函": {"type": "inquiry_letter", "score": 80},
    "关注函": {"type": "attention_letter", "score": 75},
    "诉讼": {"type": "litigation", "score": 80},
    "仲裁": {"type": "arbitration", "score": 80},
    "退市风险": {"type": "delisting_risk", "score": 90},
    "ST": {"type": "st_warning", "score": 85},
    "澄清公告": {"type": "clarification", "score": 70},
    "股票交易异常波动": {"type": "abnormal_trading", "score": 75},
    "业绩预减": {"type": "performance_decline", "score": 85},
    "亏损": {"type": "loss", "score": 80},

    # 募投变更/终止
    "终止募集资金投资项目": {"type": "fundraising_project_change", "score": 70},
    "变更募集资金投资项目": {"type": "fundraising_project_change", "score": 65},
    "终止部分募集资金": {"type": "fundraising_project_change", "score": 70},
    "募投项目延期": {"type": "fundraising_project_change", "score": 60},
    "募投项目终止": {"type": "fundraising_project_change", "score": 70},
}

# ============================================================================
# P2: 真实经营类公告（analyze）
# ============================================================================

HIGH_VALUE_KEYWORDS = {
    # 业绩
    "业绩预告": {"type": "performance_forecast", "score": 90},
    "业绩快报": {"type": "performance_express", "score": 90},

    # 合同/订单/中标
    "重大合同": {"type": "major_contract", "score": 95},
    "签订合同": {"type": "contract_signing", "score": 80},
    "中标": {"type": "bid_winning", "score": 90},
    "项目中标": {"type": "bid_winning", "score": 90},
    "订单": {"type": "order", "score": 80},

    # 并购重组
    "并购": {"type": "mna", "score": 95},
    "重组": {"type": "restructuring", "score": 95},
    "资产收购": {"type": "asset_acquisition", "score": 90},

    # 产能扩建/项目进展
    "扩建项目": {"type": "project_expansion_progress", "score": 75},
    "采选扩建": {"type": "project_expansion_progress", "score": 75},
    "产能扩建": {"type": "project_expansion_progress", "score": 75},
    "投资建设": {"type": "investment_construction", "score": 75},
    "建设项目进展": {"type": "project_expansion_progress", "score": 75},
    "募投项目建设进展": {"type": "project_expansion_progress", "score": 70},
    "控股子公司投资": {"type": "project_expansion_progress", "score": 75},

    # 真实对外投资（排除制度类）
    "对外投资设立": {"type": "external_investment", "score": 80},
    "参与设立产业基金": {"type": "external_investment", "score": 75},
    "签署投资协议": {"type": "external_investment", "score": 80},

    # 扩产/股权激励
    "扩产": {"type": "capacity_expansion", "score": 80},
    "回购股份": {"type": "share_buyback", "score": 80},
    "增持": {"type": "shareholding_increase", "score": 75},
    "股权激励": {"type": "equity_incentive", "score": 70},

    # 医药监管进展
    "EU GMP": {"type": "pharma_regulatory_progress", "score": 75},
    "GMP检查": {"type": "pharma_regulatory_progress", "score": 70},
    "药品上市申请获得受理": {"type": "pharma_regulatory_progress", "score": 85},
    "药品上市申请": {"type": "pharma_regulatory_progress", "score": 80},
    "注册申请获得受理": {"type": "pharma_regulatory_progress", "score": 80},
    "临床试验申请获批": {"type": "pharma_regulatory_progress", "score": 75},
    "IND获批": {"type": "pharma_regulatory_progress", "score": 75},
    "NDA受理": {"type": "pharma_regulatory_progress", "score": 85},
}

# ============================================================================
# P3: 股权/权益/观察类（watch）
# ============================================================================

WATCH_KEYWORDS = {
    "持股5%以上股东权益变动": {"type": "shareholder_change", "score": 40},
    "权益变动触及1%刻度": {"type": "shareholder_change", "score": 38},
    "权益变动提示": {"type": "shareholder_change", "score": 38},
    "持股比例变动": {"type": "shareholder_change", "score": 35},
    "对外担保公告": {"type": "external_guarantee", "score": 55},
    "为子公司提供担保": {"type": "external_guarantee", "score": 50},
    "担保额度预计": {"type": "external_guarantee", "score": 50},
    "违规担保": {"type": "external_guarantee", "score": 75},
    "股权转让完成": {"type": "asset_or_equity_transfer", "score": 65},
    "股权转让": {"type": "asset_or_equity_transfer", "score": 60},
    "资产出售": {"type": "asset_or_equity_transfer", "score": 65},
    "转让子公司股权": {"type": "asset_or_equity_transfer", "score": 60},
    "收购股权": {"type": "asset_or_equity_transfer", "score": 70},
    "可转债投资者适当性": {"type": "bond_or_cb_risk_notice", "score": 15},
    "债券投资者适当性": {"type": "bond_or_cb_risk_notice", "score": 15},
    "转债交易风险提示": {"type": "bond_or_cb_risk_notice", "score": 15},
}

# ============================================================================
# 其他财报类（当前watch）
# ============================================================================

REPORT_KEYWORDS = {
    "年度报告": {"type": "annual_report", "score": 50},
    "半年度报告": {"type": "semi_annual_report", "score": 50},
    "季度报告": {"type": "quarterly_report", "score": 50},
}

# 低价值流程类
LOW_VALUE_KEYWORDS = {
    "停复牌": {"type": "trading_status_notice", "score": 25},
    "复牌": {"type": "trading_status_notice", "score": 25},
    "停牌": {"type": "trading_status_notice", "score": 25},
    "摘牌": {"type": "trading_status_notice", "score": 25},
    "权益分派实施": {"type": "dividend_implementation", "score": 12},
    "权益分派": {"type": "dividend_implementation", "score": 12},
    "分红派息": {"type": "dividend_implementation", "score": 12},
    "派息实施": {"type": "dividend_implementation", "score": 12},
    "募集说明书": {"type": "prospectus", "score": 15},
}


def classify_announcement_type(title: str, announcement_type_raw: str = "") -> dict:
    """
    根据优先级P0-P4分类公告

    优先级顺序：
    P0: 流程/制度/治理类（archive）
    P1: 真实风险类（risk_review）
    P2: 真实经营类（analyze）
    P3: 权益/观察类（watch）
    P4: 未知类（watch, 低分）

    Args:
        title: 公告标题
        announcement_type_raw: 原始公告类型

    Returns:
        {
            "announcement_type": "...",
            "category": "routine/risk/business/watch/unknown",
            "pre_score": int,
            "matched_keyword": "...",
            "priority": "P0/P1/P2/P3/P4"
        }
    """
    title_lower = title.lower()
    raw_lower = announcement_type_raw.lower()
    text = f"{title_lower} {raw_lower}"
    text_original = f"{title} {announcement_type_raw}"  # 保留原始大小写用于特殊匹配

    # P0: 流程/制度/治理类（最高优先级）
    # 强制优先：如果包含制度/规则/细则/章程，即使有投资/担保等词也archive
    for keyword, info in ROUTINE_GOVERNANCE_KEYWORDS.items():
        if keyword in text:
            # 特殊检查：避免"对外投资管理制度"误判为external_investment
            return {
                "announcement_type": info["type"],
                "category": "routine",
                "pre_score": info["score"],
                "matched_keyword": keyword,
                "priority": "P0"
            }

    # 其他低价值治理类（在会议决议之前匹配，更具体）
    for keyword, info in OTHER_ROUTINE_KEYWORDS.items():
        if keyword in text:
            return {
                "announcement_type": info["type"],
                "category": "routine",
                "pre_score": info["score"],
                "matched_keyword": keyword,
                "priority": "P0"
            }

    # 会议/决议/通知类（相对泛化，放后面）
    for keyword, info in MEETING_NOTICE_KEYWORDS.items():
        if keyword in text:
            return {
                "announcement_type": info["type"],
                "category": "routine",
                "pre_score": info["score"],
                "matched_keyword": keyword,
                "priority": "P0"
            }

    # P1: 真实风险类
    for keyword, info in RISK_KEYWORDS.items():
        if keyword in text:
            return {
                "announcement_type": info["type"],
                "category": "risk",
                "pre_score": info["score"],
                "matched_keyword": keyword,
                "priority": "P1"
            }

    # P2: 真实经营类
    # 特殊检查：EU GMP（大写）
    if "EU GMP" in text_original or "GMP检查" in text:
        return {
            "announcement_type": "pharma_regulatory_progress",
            "category": "business",
            "pre_score": 70,
            "matched_keyword": "EU GMP" if "EU GMP" in text_original else "GMP检查",
            "priority": "P2"
        }

    for keyword, info in HIGH_VALUE_KEYWORDS.items():
        if keyword in text:
            return {
                "announcement_type": info["type"],
                "category": "business",
                "pre_score": info["score"],
                "matched_keyword": keyword,
                "priority": "P2"
            }

    # P3: 权益/观察类
    for keyword, info in WATCH_KEYWORDS.items():
        if keyword in text:
            return {
                "announcement_type": info["type"],
                "category": "watch",
                "pre_score": info["score"],
                "matched_keyword": keyword,
                "priority": "P3"
            }

    # 财报类
    for keyword, info in REPORT_KEYWORDS.items():
        if keyword in text:
            return {
                "announcement_type": info["type"],
                "category": "watch",
                "pre_score": info["score"],
                "matched_keyword": keyword,
                "priority": "P3"
            }

    # 低价值流程类
    for keyword, info in LOW_VALUE_KEYWORDS.items():
        if keyword in text:
            return {
                "announcement_type": info["type"],
                "category": "routine",
                "pre_score": info["score"],
                "matched_keyword": keyword,
                "priority": "P0"
            }

    # P4: 未知类（降低默认分数）
    # 如果标题包含制度/规则等但没命中，仍archive
    if any(kw in text for kw in ["制度", "规则", "细则", "章程", "修订", "会议", "决议", "通知"]):
        return {
            "announcement_type": "routine_unclassified",
            "category": "routine",
            "pre_score": 10,
            "matched_keyword": "流程类未分类",
            "priority": "P0"
        }

    return {
        "announcement_type": "unclassified",
        "category": "unknown",
        "pre_score": 18,  # 从30降到18
        "matched_keyword": "",
        "priority": "P4"
    }


__all__ = [
    'ROUTINE_GOVERNANCE_KEYWORDS',
    'MEETING_NOTICE_KEYWORDS',
    'RISK_KEYWORDS',
    'HIGH_VALUE_KEYWORDS',
    'WATCH_KEYWORDS',
    'classify_announcement_type'
]
