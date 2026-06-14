"""
SEC 财报内容压缩器
将30000字符的8-K财报压缩到8000-12000字符，保留关键财务信息
"""
import re
from typing import Dict, Any, List


# 关键词权重
HIGH_VALUE_KEYWORDS = {
    'revenue': 10,
    'revenues': 10,
    'quarterly revenue': 10,
    'data center': 10,
    'datacenter': 10,
    'diluted eps': 10,
    'earnings per share': 10,
    'gross margin': 10,
    'outlook': 10,
    'guidance': 10,
    'next quarter': 10,
    'expects': 10,
}

MEDIUM_VALUE_KEYWORDS = {
    'net income': 6,
    'operating income': 6,
    'operating margin': 6,
    'cash flow': 6,
    'free cash flow': 6,
    'share repurchase': 6,
    'buyback': 6,
    'dividend': 6,
    'fiscal': 6,
}

INDUSTRY_KEYWORDS = {
    'gaming': 4,
    'automotive': 4,
    'professional visualization': 4,
    'ai': 4,
    'accelerated computing': 4,
    'cloud': 4,
}

LOW_VALUE_KEYWORDS = {
    'safe harbor': -10,
    'forward-looking statements': -10,
    'investor relations': -10,
    'media contact': -10,
    'copyright': -10,
    'trademark': -10,
    'no obligation to update': -10,
    'legal disclaimer': -10,
    'forward looking statements': -10,
}


def reduce_sec_content_for_ai(filing: Dict[str, Any], max_chars: int = 12000) -> str:
    """
    压缩SEC filing内容用于AI分析

    Args:
        filing: Filing数据
        max_chars: 最大字符数

    Returns:
        压缩后的内容
    """
    content = filing.get('content', '')

    if not content:
        return ""

    # 检查是否为财报类filing
    is_earnings = (
        filing.get('source') == 'sec_edgar' and
        filing.get('event_hint') == 'earnings_release' and
        filing.get('form_type') in ['8-K', '8-K/A']
    )

    # 非财报类，直接截断
    if not is_earnings:
        return content[:max_chars]

    # 财报类，智能压缩
    # 1. 构建header
    header = _build_header(filing)
    header_len = len(header)

    # 2. 分块
    blocks = split_content_blocks(content)

    # 3. 对每个block压缩
    remaining_chars = max_chars - header_len - 100  # 留100字符buffer
    reduced_blocks = []

    for block in blocks:
        # 分配字符配额（按block重要性）
        if 'EX-99.1' in block['block_name']:
            block_quota = int(remaining_chars * 0.45)  # 45%给Press Release
        elif 'EX-99.2' in block['block_name']:
            block_quota = int(remaining_chars * 0.35)  # 35%给CFO Commentary
        else:
            block_quota = int(remaining_chars * 0.20)  # 20%给Primary

        reduced_text = reduce_block(block, block_quota)

        if reduced_text:
            reduced_blocks.append({
                'block_name': block['block_name'],
                'text': reduced_text
            })

    # 4. 组装最终输出
    output_parts = [header]

    for block in reduced_blocks:
        separator = f"\n\n{'='*50}\n{block['block_name']}\n{'='*50}\n"
        output_parts.append(separator)
        output_parts.append(block['text'])

    final_output = '\n'.join(output_parts)

    # 5. 最终截断（以防超长）
    if len(final_output) > max_chars:
        final_output = final_output[:max_chars] + "\n\n[Content truncated at max length]"

    return final_output


def _build_header(filing: Dict[str, Any]) -> str:
    """构建header"""
    ticker = filing.get('ticker', 'UNKNOWN')
    company_name = filing.get('company_name', 'UNKNOWN')
    form_type = filing.get('form_type', '8-K')
    filing_date = filing.get('filing_date', 'UNKNOWN')
    items = filing.get('items', [])
    event_hint = filing.get('event_hint', '')

    header = f"""SEC EDGAR Filing Summary Input
Ticker: {ticker}
Company: {company_name}
Form: {form_type}
Filing Date: {filing_date}
Items: {', '.join(items)}
Event Hint: {event_hint}
"""
    return header


def split_content_blocks(content: str) -> List[Dict[str, str]]:
    """
    按Exhibit分块

    Returns:
        [{"block_name": "...", "text": "..."}, ...]
    """
    blocks = []

    # 查找Exhibit分隔符
    # 真实格式: ========== EXHIBIT EX-99.1 | Press Release ==========
    # 或: EXHIBIT EX-99.1 | Press Release (前后可能有=号)
    # 策略：先找所有包含EXHIBIT EX-的行，然后检查前后是否有=号
    lines = content.split('\n')
    exhibit_positions = []

    for i, line in enumerate(lines):
        # 检查是否包含EXHIBIT EX-
        if re.search(r'EXHIBIT\s+EX-[\d.]+', line, re.IGNORECASE):
            # 检查前后是否有=号
            has_separator = '=' in line or (i > 0 and '=' in lines[i-1]) or (i < len(lines)-1 and '=' in lines[i+1])
            if has_separator:
                # 提取exhibit类型和描述
                ex_match = re.search(r'EXHIBIT\s+(EX-[\d.]+)\s*\|?\s*([^\n=]+)', line, re.IGNORECASE)
                if ex_match:
                    exhibit_type = ex_match.group(1).upper()
                    exhibit_desc = ex_match.group(2).strip()
                    # 计算字符位置
                    char_pos = len('\n'.join(lines[:i]))
                    exhibit_positions.append({
                        'pos': char_pos,
                        'line': i,
                        'type': exhibit_type,
                        'desc': exhibit_desc
                    })

    if not exhibit_positions:
        # 没有Exhibit，整个作为primary
        return [{'block_name': 'PRIMARY DOCUMENT', 'text': content}]

    # 按位置排序
    exhibit_positions.sort(key=lambda x: x['pos'])

    # 提取primary（第一个Exhibit之前的部分）
    if exhibit_positions[0]['pos'] > 100:  # 至少100字符才算有primary
        primary_text = content[:exhibit_positions[0]['pos']].strip()
        if len(primary_text) > 100:
            blocks.append({'block_name': 'PRIMARY DOCUMENT', 'text': primary_text})

    # 提取每个Exhibit
    for i, ex_info in enumerate(exhibit_positions):
        block_name = f"EXHIBIT {ex_info['type']} | {ex_info['desc']}"

        # Exhibit内容：从当前位置到下一个Exhibit（或文档结尾）
        start = ex_info['pos']
        # 跳过分隔符行本身（向前找到下一个非分隔符行）
        start_search = start
        for j in range(ex_info['line'], len(lines)):
            if lines[j].strip() and not all(c in '= \t' for c in lines[j]):
                start = len('\n'.join(lines[:j+1]))
                break

        end = exhibit_positions[i + 1]['pos'] if i + 1 < len(exhibit_positions) else len(content)

        exhibit_text = content[start:end].strip()

        if len(exhibit_text) > 100:  # 至少100字符
            blocks.append({'block_name': block_name, 'text': exhibit_text})

    # 如果还是没有blocks，返回整个content
    if not blocks:
        blocks = [{'block_name': 'PRIMARY DOCUMENT', 'text': content}]

    return blocks


def split_paragraphs(text: str) -> List[str]:
    """按段落切分"""
    # 策略1: 按双换行分段
    paragraphs = re.split(r'\n\s*\n', text)

    # 如果段落太少（文本可能没有双换行），尝试单换行
    if len(paragraphs) < 5:
        paragraphs = text.split('\n')

    # 如果段落还是太少，按句号分段
    if len(paragraphs) < 5:
        paragraphs = re.split(r'\.\s+', text)

    # 过滤空段落和太短的段落
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 30]

    # 如果段落太长，进一步切分
    final_paragraphs = []
    for para in paragraphs:
        if len(para) > 1000:
            # 大段落按句号切分
            sub_paras = re.split(r'\.\s+', para)
            final_paragraphs.extend([s.strip() for s in sub_paras if s.strip() and len(s.strip()) > 30])
        else:
            final_paragraphs.append(para)

    return final_paragraphs


def score_paragraph(paragraph: str) -> int:
    """
    给段落打分

    Returns:
        分数（高分=重要，负分=删除）
    """
    para_lower = paragraph.lower()
    score = 0

    # 高价值关键词
    for keyword, weight in HIGH_VALUE_KEYWORDS.items():
        if keyword in para_lower:
            score += weight

    # 中价值关键词
    for keyword, weight in MEDIUM_VALUE_KEYWORDS.items():
        if keyword in para_lower:
            score += weight

    # 行业关键词
    for keyword, weight in INDUSTRY_KEYWORDS.items():
        if keyword in para_lower:
            score += weight

    # 低价值关键词（负分）
    for keyword, weight in LOW_VALUE_KEYWORDS.items():
        if keyword in para_lower:
            score += weight

    return score


def reduce_block(block: Dict[str, str], max_block_chars: int) -> str:
    """
    压缩单个block

    Args:
        block: {"block_name": "...", "text": "..."}
        max_block_chars: 最大字符数

    Returns:
        压缩后的文本
    """
    text = block['text']

    if len(text) <= max_block_chars:
        return text

    # 分段
    paragraphs = split_paragraphs(text)

    # 打分
    scored_paras = []
    for para in paragraphs:
        score = score_paragraph(para)
        scored_paras.append({
            'text': para,
            'score': score,
            'length': len(para)
        })

    # 按分数排序
    scored_paras.sort(key=lambda x: x['score'], reverse=True)

    # 贪心选择：优先选高分段落，直到达到长度限制
    selected = []
    current_length = 0

    for para in scored_paras:
        # 跳过负分段落
        if para['score'] < 0:
            continue

        if current_length + para['length'] + 2 <= max_block_chars:  # +2为换行
            selected.append(para)
            current_length += para['length'] + 2

    # 按原始顺序重新排列（保持逻辑连贯）
    # 通过段落文本匹配原始位置
    original_order = []
    for para_obj in selected:
        idx = paragraphs.index(para_obj['text']) if para_obj['text'] in paragraphs else 999
        original_order.append((idx, para_obj['text']))

    original_order.sort(key=lambda x: x[0])

    # 组装
    result = '\n\n'.join([p[1] for p in original_order])

    return result


__all__ = ['reduce_sec_content_for_ai']
