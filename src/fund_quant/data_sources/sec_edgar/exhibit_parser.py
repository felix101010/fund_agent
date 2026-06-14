"""
Exhibit 解析器
解析index.json，筛选重要附件
"""
from typing import List, Dict, Any, Optional

from fund_quant.data_sources.sec_edgar.sec_rules_config import IMPORTANT_EXHIBIT_TYPES, EXHIBIT_PRIORITY
from fund_quant.data_sources.sec_edgar.url_builder import SECURLBuilder


class ExhibitParser:
    """
    Exhibit 解析器

    职责：
    1. 解析index.json
    2. 筛选重要附件
    3. 构建附件URL
    """

    @staticmethod
    def parse_index_json(
        index_json: Dict[str, Any],
        cik: str,
        accession_number: str
    ) -> List[Dict[str, Any]]:
        """
        解析index.json，提取重要附件

        Args:
            index_json: index.json内容
            cik: CIK
            accession_number: Accession number

        Returns:
            附件列表 [{type, filename, description, url, priority}]

        Note:
            SEC index.json的type字段是"text.gif"等，不是"EX-99.1"
            需要通过filename模式匹配识别附件
        """
        exhibits = []

        # 获取directory.item列表
        directory = index_json.get('directory', {})
        items = directory.get('item', [])

        if not items:
            return exhibits

        # 遍历文件
        for item in items:
            filename = item.get('name', '').lower()

            # 通过文件名模式匹配
            exhibit_type, description = ExhibitParser._classify_by_filename(filename)

            if not exhibit_type:
                continue

            # 构建URL
            url = SECURLBuilder.build_exhibit_url(cik, accession_number, item.get('name', ''))

            # 获取优先级
            priority = ExhibitParser._get_exhibit_priority(exhibit_type)

            exhibits.append({
                'type': exhibit_type,
                'filename': item.get('name', ''),
                'description': description,
                'url': url,
                'priority': priority
            })

        # 按优先级排序
        exhibits.sort(key=lambda x: x['priority'], reverse=True)

        return exhibits

    @staticmethod
    def _classify_by_filename(filename: str) -> tuple:
        """
        根据文件名模式分类附件

        Args:
            filename: 文件名（小写）

        Returns:
            (exhibit_type, description) 或 (None, None)

        Examples:
            >>> _classify_by_filename("q1fy27pr.htm")
            ('EX-99.1', 'Press Release')

            >>> _classify_by_filename("q1fy27cfocommentary.htm")
            ('EX-99.2', 'CFO Commentary')

            >>> _classify_by_filename("ex991.htm")
            ('EX-99.1', 'Exhibit 99.1')
        """
        # 模式1: pr / press / pressrelease
        if any(pattern in filename for pattern in ['pr.htm', 'press', 'pressrelease']):
            return ('EX-99.1', 'Press Release')

        # 模式2: cfo / cfocommentary / commentary
        if any(pattern in filename for pattern in ['cfo', 'commentary']):
            return ('EX-99.2', 'CFO Commentary')

        # 模式3: ex99 / ex-99 / exhibit99
        if 'ex99' in filename or 'ex-99' in filename or 'exhibit99' in filename:
            if '991' in filename or '99.1' in filename:
                return ('EX-99.1', 'Exhibit 99.1')
            elif '992' in filename or '99.2' in filename:
                return ('EX-99.2', 'Exhibit 99.2')
            else:
                return ('EX-99', 'Exhibit 99')

        # 模式4: ex10 / ex-10
        if 'ex10' in filename or 'ex-10' in filename:
            return ('EX-10', 'Material Agreement')

        # 模式5: ex2 / ex-2 (M&A)
        if 'ex2' in filename or 'ex-2' in filename:
            return ('EX-2', 'M&A Agreement')

        return (None, None)

    @staticmethod
    def _is_important_exhibit(exhibit_type: str) -> bool:
        """
        判断是否为重要附件

        Args:
            exhibit_type: 附件类型（例如 "EX-99.1"）

        Returns:
            是否重要
        """
        if not exhibit_type:
            return False

        exhibit_type_upper = exhibit_type.upper()

        # 精确匹配
        if exhibit_type_upper in IMPORTANT_EXHIBIT_TYPES:
            return True

        # 前缀匹配
        for important_type in IMPORTANT_EXHIBIT_TYPES:
            if exhibit_type_upper.startswith(important_type):
                return True

        return False

    @staticmethod
    def _get_exhibit_priority(exhibit_type: str) -> int:
        """
        获取附件优先级

        Args:
            exhibit_type: 附件类型

        Returns:
            优先级（0-100）
        """
        exhibit_type_upper = exhibit_type.upper()

        # 精确匹配
        if exhibit_type_upper in EXHIBIT_PRIORITY:
            return EXHIBIT_PRIORITY[exhibit_type_upper]

        # 前缀匹配
        for key, priority in EXHIBIT_PRIORITY.items():
            if exhibit_type_upper.startswith(key):
                return priority

        return 50  # 默认优先级

    @staticmethod
    def _get_exhibit_description(exhibit_type: str) -> str:
        """
        获取附件描述

        Args:
            exhibit_type: 附件类型

        Returns:
            描述
        """
        description_map = {
            'EX-99.1': 'Press Release',
            'EX-99.2': 'CFO Commentary',
            'EX-99': 'Additional Information',
            'EX-10': 'Material Agreement',
            'EX-2.1': 'M&A Agreement',
            'EX-2': 'M&A Plan'
        }

        exhibit_type_upper = exhibit_type.upper()

        # 精确匹配
        if exhibit_type_upper in description_map:
            return description_map[exhibit_type_upper]

        # 前缀匹配
        for key, desc in description_map.items():
            if exhibit_type_upper.startswith(key):
                return desc

        return 'Exhibit'


__all__ = ['ExhibitParser']
