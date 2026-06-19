"""
标题公司名提取器
从新闻标题中用规则提取显式公司名
"""
import re
from dataclasses import dataclass, field
from typing import List


# 标题公司名黑名单（非上市公司、政府、媒体、人物、国家）
TITLE_COMPANY_BLACKLIST = {
    # 政府机构
    "国家统计局", "发改委", "工信部", "商务部", "财政部", "央行",
    "中央气象台", "国家防总", "应急管理部",

    # 媒体
    "央视新闻", "新华社", "财联社", "科创板日报", "证券时报",

    # 券商研究机构
    "中信证券", "中金公司", "国泰君安", "华泰证券", "招商证券",

    # 人物/消息源
    "业内人士", "知情人士", "消息人士", "分析师", "专家",

    # 国家/地区
    "特朗普", "伊朗", "以色列", "美国", "英国", "俄罗斯", "乌克兰",
    "菲律宾", "墨西哥", "中国香港", "香港", "台湾", "澳门",

    # 其他
    "这家公司", "该公司", "相关公司", "A公司", "B公司", "某公司"
}


@dataclass
class TitleCompanyCandidate:
    """标题公司名候选"""
    name: str
    matched_text: str
    pattern_name: str
    confidence: float


class TitleCompanyExtractor:
    """
    标题公司名提取器

    职责：
    1. 从标题用规则提取显式公司名
    2. 黑名单过滤
    3. 不做股票代码判断
    """

    def __init__(self):
        """初始化"""
        self.blacklist = TITLE_COMPANY_BLACKLIST

        # 编译正则模式
        self.patterns = [
            # 公司名：事件
            {
                'name': 'colon_prefix',
                'regex': re.compile(r'^([一-龥A-Za-z0-9·（）()]{2,20})[:：]'),
                'confidence': 0.95
            },
            # 公司名(代码) / 公司名（代码）
            {
                'name': 'company_with_code',
                'regex': re.compile(r'([一-龥A-Za-z0-9·（）()]{2,20})[（(](\d{6}\.(SH|SZ|BJ))[）)]'),
                'confidence': 0.98
            },
            # 公司名公告称 / 公司名公告 / 公司名披露 / 公司名发布
            {
                'name': 'announcement_verb',
                'regex': re.compile(r'^([一-龥A-Za-z0-9·（）()]{2,20})(公告称|公告|披露|发布)'),
                'confidence': 0.90
            },
            # 公司名在互动平台表示 / 回复称 / 回应称 / 表示 / 称
            {
                'name': 'response_verb',
                'regex': re.compile(r'^([一-龥A-Za-z0-9·（）()]{2,20})(在互动平台表示|回复称|回应称|表示|称)'),
                'confidence': 0.88
            },
        ]

    def extract(self, title: str) -> List[TitleCompanyCandidate]:
        """
        从标题提取公司名候选

        Args:
            title: 新闻标题

        Returns:
            公司名候选列表
        """
        if not title:
            return []

        candidates = []

        for pattern in self.patterns:
            match = pattern['regex'].search(title)
            if match:
                company_name = match.group(1).strip()

                # 黑名单过滤
                if company_name in self.blacklist:
                    continue

                # 长度检查
                if len(company_name) < 2 or len(company_name) > 20:
                    continue

                # 避免重复
                if any(c.name == company_name for c in candidates):
                    continue

                candidate = TitleCompanyCandidate(
                    name=company_name,
                    matched_text=match.group(0),
                    pattern_name=pattern['name'],
                    confidence=pattern['confidence']
                )
                candidates.append(candidate)

        return candidates


__all__ = ['TitleCompanyExtractor', 'TitleCompanyCandidate', 'TITLE_COMPANY_BLACKLIST']
