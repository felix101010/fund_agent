"""
内容合并器
合并primary document和exhibits
"""
from typing import List, Dict, Any


class ContentMerger:
    """
    内容合并器

    职责：
    合并primary document和exhibits，控制总长度
    """

    @staticmethod
    def merge_primary_and_exhibits(
        primary_text: str,
        exhibits: List[Dict[str, Any]],
        max_chars: int = 30000
    ) -> str:
        """
        合并primary和exhibits

        Args:
            primary_text: Primary document正文
            exhibits: Exhibit列表
            max_chars: 最大字符数

        Returns:
            合并后的文本

        格式:
            primary_text

            ========== EXHIBIT EX-99.1 | Press Release ==========
            exhibit_text

            ========== EXHIBIT EX-99.2 | CFO Commentary ==========
            exhibit_text
        """
        if not primary_text:
            primary_text = ""

        # 如果没有附件，直接返回primary
        if not exhibits:
            return primary_text[:max_chars]

        # 计算primary占用空间
        primary_len = len(primary_text)

        # 如果primary已经超长，截断并返回
        if primary_len >= max_chars:
            return primary_text[:max_chars] + "\n\n[Content truncated at max length]"

        # 开始构建合并内容
        merged = primary_text
        remaining_space = max_chars - primary_len

        # 过滤成功下载的附件
        successful_exhibits = [
            ex for ex in exhibits
            if ex.get('download_status') == 'success' and ex.get('text')
        ]

        if not successful_exhibits:
            return merged

        # 按优先级添加附件（已经排序）
        for exhibit in successful_exhibits:
            # 构建分隔符
            exhibit_type = exhibit.get('type', 'EX-?')
            description = exhibit.get('description', 'Exhibit')
            separator = f"\n\n{'='*50}\nEXHIBIT {exhibit_type} | {description}\n{'='*50}\n\n"

            exhibit_text = exhibit.get('text', '')

            # 计算需要的空间
            needed_space = len(separator) + len(exhibit_text)

            # 如果空间不足，尝试截断
            if needed_space > remaining_space:
                # 至少保留分隔符
                if len(separator) < remaining_space:
                    available_for_text = remaining_space - len(separator) - 50  # 留50字符给提示
                    if available_for_text > 100:  # 至少100字符才有意义
                        merged += separator
                        merged += exhibit_text[:available_for_text]
                        merged += "\n\n[Exhibit truncated due to length limit]"
                break
            else:
                # 空间足够，添加完整附件
                merged += separator
                merged += exhibit_text
                remaining_space -= needed_space

        return merged


__all__ = ['ContentMerger']
