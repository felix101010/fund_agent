"""
SEC 8-K Item 解析器
从8-K正文中提取Item编号
"""
import re
from typing import List


class Sec8KItemParser:
    """
    SEC 8-K Item 解析器

    职责：
    从8-K filing正文中提取Item编号
    """

    # 正则模式：匹配 "Item 2.02" 或 "Item\n2.02" 等变体
    ITEM_PATTERN = re.compile(r'Item\s+(\d+\.\d+)', re.IGNORECASE)

    @staticmethod
    def extract_8k_items(content: str) -> List[str]:
        """
        提取8-K Item编号

        Args:
            content: 8-K正文

        Returns:
            Item编号列表，已排序去重

        Examples:
            >>> extract_8k_items("Item 2.02 Results of Operations\\nItem 9.01 Financial Statements")
            ['2.02', '9.01']

            >>> extract_8k_items("ITEM 5.02 and Item 5.02 again")
            ['5.02']

            >>> extract_8k_items("")
            []
        """
        if not content:
            return []

        # 使用正则查找所有匹配
        matches = Sec8KItemParser.ITEM_PATTERN.findall(content)

        if not matches:
            return []

        # 去重
        unique_items = list(set(matches))

        # 排序（按数字排序）
        unique_items.sort(key=lambda x: float(x))

        return unique_items


__all__ = ['Sec8KItemParser']
