"""
SEC 规则配置
8-K Item映射、优先级、Exhibit类型
"""

# 8-K Item 到事件类型映射
SEC_8K_ITEM_EVENT_MAP = {
    "1.01": "material_agreement",        # 重大协议
    "1.02": "property_acquisition",      # 资产收购
    "1.03": "bankruptcy",                # 破产
    "2.01": "mna_completed",            # 并购完成
    "2.02": "earnings_release",         # 财报发布
    "2.03": "unregistered_sale",        # 非注册证券出售
    "2.04": "triggering_events",        # 触发事件
    "2.05": "restructuring",            # 重组
    "2.06": "impairment",               # 减值
    "3.01": "delisting_risk",           # 退市风险
    "3.02": "financing",                # 融资
    "3.03": "material_modification",    # 重大修改
    "4.01": "management_change",        # 管理层变动
    "4.02": "non_reliance",             # 财务报表不可依赖
    "5.01": "aml_change",               # 会计/审计变更
    "5.02": "executive_change",         # 董事/高管变动
    "5.03": "bankruptcy_appointment",   # 破产受托人任命
    "5.04": "interim_cfo",              # 临时CFO
    "5.05": "compensation_change",      # 薪酬变更
    "5.07": "shareholder_director",     # 股东提名董事
    "5.08": "compensation_policy",      # 薪酬政策
    "7.01": "business_update",          # 业务更新
    "8.01": "other_material_event",     # 其他重大事件
    "9.01": "exhibits",                 # 附件
}

# 8-K Item 优先级评分（用于pre_score）
SEC_8K_ITEM_PRIORITY = {
    "3.01": 95,   # 退市风险 - 最高
    "2.02": 90,   # 财报发布
    "1.01": 85,   # 重大协议
    "2.01": 85,   # 并购完成
    "2.06": 85,   # 减值
    "5.02": 80,   # 董事/高管变动
    "3.02": 75,   # 融资
    "2.05": 75,   # 重组
    "1.03": 75,   # 破产
    "8.01": 70,   # 其他重大事件
    "4.02": 70,   # 财务报表不可依赖
    "7.01": 65,   # 业务更新
    "5.01": 60,   # 会计/审计变更
    "1.02": 60,   # 资产收购
    "3.02": 55,   # 融资
    "5.03": 50,   # 薪酬变更
    "2.03": 45,   # 非注册证券出售
    "9.01": 40,   # 仅附件
}

# 重要Exhibit类型
IMPORTANT_EXHIBIT_TYPES = [
    "EX-99.1",   # 新闻稿
    "EX-99.2",   # CFO评论/补充信息
    "EX-99",     # 其他附件
    "EX-10",     # 重大合同
    "EX-2.1",    # 并购协议
    "EX-2",      # 并购计划
]

# Exhibit优先级（用于截断时排序）
EXHIBIT_PRIORITY = {
    "EX-99.1": 100,  # 新闻稿 - 最高
    "EX-99.2": 90,   # CFO评论
    "EX-10": 80,     # 重大合同
    "EX-2.1": 75,    # 并购协议
    "EX-2": 75,      # 并购计划
    "EX-99": 70,     # 其他附件
}

# 高管关键词（用于risk_flags）
EXECUTIVE_KEYWORDS = [
    "CEO", "CFO", "COO", "CTO", "Chief Executive",
    "Chief Financial", "Chief Operating", "Chief Technology",
    "resignation", "resign", "retire", "retirement",
    "departure", "terminated", "accounting officer"
]

# 风险关键词（用于risk_flags）
RISK_KEYWORDS = {
    "delisting": "delisting_risk",
    "bankruptcy": "bankruptcy_risk",
    "going concern": "going_concern_risk",
    "restatement": "restatement_risk",
    "investigation": "investigation_risk",
    "litigation": "litigation_risk",
    "default": "default_risk",
    "impairment": "impairment_risk"
}


__all__ = [
    'SEC_8K_ITEM_EVENT_MAP',
    'SEC_8K_ITEM_PRIORITY',
    'IMPORTANT_EXHIBIT_TYPES',
    'EXHIBIT_PRIORITY',
    'EXECUTIVE_KEYWORDS',
    'RISK_KEYWORDS'
]
