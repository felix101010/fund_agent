"""
SEC 8-K 事件抽取 Prompt
专用于SEC EDGAR 8-K filing的AI事件抽取
"""
from typing import Dict, Any


def build_sec_8k_event_prompt(filing: Dict[str, Any]) -> str:
    """
    构建SEC 8-K事件抽取Prompt

    Args:
        filing: Filing数据（包含ticker, company_name, items, event_hint, content等）

    Returns:
        Prompt文本
    """
    # 提取字段
    ticker = filing.get('ticker', 'UNKNOWN')
    company_name = filing.get('company_name', 'UNKNOWN')
    form_type = filing.get('form_type', '8-K')
    filing_date = filing.get('filing_date', 'UNKNOWN')
    items = filing.get('items', [])
    event_hint = filing.get('event_hint', '')
    pre_score = filing.get('pre_score', 0)
    sec_rule_reason = filing.get('sec_rule_reason', '')
    has_exhibits = filing.get('has_exhibits', False)
    exhibit_count = filing.get('exhibit_count', 0)
    content = filing.get('content', '')

    # 构建Exhibit说明
    exhibits_info = ""
    if has_exhibits and exhibit_count > 0:
        exhibits = filing.get('exhibits', [])
        exhibit_types = [ex.get('type', '') for ex in exhibits if ex.get('download_status') == 'success']
        if exhibit_types:
            exhibits_info = f"""
本filing包含{exhibit_count}个重要附件：{', '.join(exhibit_types)}
正文中的"EXHIBIT"分隔符标记了各个附件的起始位置。
请重点分析附件内容，因为附件通常包含最关键的信息（如新闻稿、财务数据、CFO评论等）。
"""

    # 构建Prompt
    prompt = f"""你是一个专业的SEC EDGAR filing分析专家。

重要提示：
1. 这是SEC官方正式filing（Form {form_type}），不是普通新闻或市场传闻。
2. SEC filing具有法律约束力，信息准确性高。
3. 不要编造正文中没有的财务数字。
4. 如果某个指标未找到，必须填写"unknown"。

Filing基础信息：
- Ticker: {ticker}
- Company: {company_name}
- Form: {form_type}
- Filing Date: {filing_date}
- Items: {', '.join(items) if items else 'Unknown'}
- Event Hint: {event_hint}
- Pre-Score: {pre_score}
- SEC Rule Reason: {sec_rule_reason}
{exhibits_info}

8-K Items说明（供参考）：
- Item 2.02: 财报/业绩披露
- Item 5.02: 董事/高管变动
- Item 1.01: 重大协议签订
- Item 2.01: 并购完成
- Item 3.01: 退市风险
- Item 8.01: 其他重大事件
- Item 9.01: 附件说明

分析任务：
请分析以下8-K filing正文，提取关键事件信息。

event_type候选（必须从以下选择）：
- earnings_release: 财报发布
- guidance_update: 指引更新
- material_agreement: 重大协议
- mna_completed: 并购完成
- executive_change: 高管变动
- financing: 融资事项
- share_buyback: 股票回购
- dividend: 分红
- stock_split: 拆股
- major_contract: 重大合同
- product_update: 产品更新
- litigation_regulatory: 诉讼/监管
- delisting_risk: 退市风险
- accounting_issue: 会计问题
- bankruptcy_restructuring: 破产/重组
- business_update: 业务更新
- exhibits_only: 仅附件说明
- other_material_event: 其他重大事件

event_level规则：
- S: 极强事件（破产、退市、重大超预期财报、重大并购）
- A: 高价值事件（财报披露、重大协议、CEO/CFO离职、重大回购）
- B: 中等事件（普通高管变动、业务更新）
- C: 低价值事件（普通董事任命、附件说明）
- D: 几乎无交易价值

financial_metrics要求（财报类事件必填，其他类型可全部unknown）：
- revenue: 营收，必须带单位，例如"$26.0 billion"或"unknown"
- eps: 每股收益，例如"$5.16"或"unknown"
- gross_margin: 毛利率，例如"75.1%"或"unknown"
- data_center_revenue: 数据中心营收（NVDA/AMD等），例如"$22.6 billion"或"unknown"
- guidance: 下季度指引，例如"Q2 revenue $28 billion"或"unknown"
- outlook: 展望，简要描述或"unknown"

management_changes要求（高管变动类事件必填）：
- person: 人员姓名
- role: 职位（CEO/CFO/COO/CTO/Board Member等）
- action: 动作（resignation/appointment/retirement/termination）
- effective_date: 生效日期
- risk_level: low（普通董事）/ medium（VP/SVP）/ high（CEO/CFO/CAO）

输出要求：
1. 必须输出合法JSON，不要输出markdown code block，不要输出解释文字
2. 直接输出JSON object，不要有任何前缀或后缀
3. summary_zh用中文，其他字段用英文
4. key_facts是数组，列出3-5个关键事实
5. risk_flags是数组，如果发现风险（CEO离职、诉讼、退市等）就加入

Filing正文：
{content[:25000]}

请分析并输出JSON（不要markdown，不要解释）：
"""

    return prompt


__all__ = ['build_sec_8k_event_prompt']
