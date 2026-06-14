"""
Filing 标准化器
将SEC filing转换为系统统一的事件输入格式
"""
from typing import Dict, Any
from datetime import datetime

from fund_quant.data_sources.sec_edgar.filing_collector import FilingMetadata


class FilingNormalizer:
    """
    Filing 标准化器

    职责：
    将SEC filing转换为系统统一格式，对接现有的规则过滤和AI抽取流程
    """

    @staticmethod
    def normalize(
        filing: FilingMetadata,
        content: str,
        items: list = None,
        event_hint: str = "",
        pre_score: int = 0,
        sec_rule_reason: str = "",
        risk_flags: list = None,
        exhibits: list = None
    ) -> Dict[str, Any]:
        """
        标准化filing为统一事件输入格式

        Args:
            filing: Filing元数据
            content: Filing正文（已合并exhibits）
            items: 8-K Item列表（例如 ["2.02", "9.01"]）
            event_hint: 事件类型提示
            pre_score: SEC规则预评分
            sec_rule_reason: SEC规则判断理由
            risk_flags: 风险标记
            exhibits: Exhibit列表

        Returns:
            统一格式的事件数据
        """
        # 生成title
        title = FilingNormalizer._generate_title(filing)

        # 解析publish_time
        publish_time = FilingNormalizer._parse_publish_time(filing)

        # 构建统一格式
        normalized = {
            # 必填字段（兼容NewsItem）
            "source": "sec_edgar",
            "news_id": filing.filing_id,
            "title": title,
            "content": content,
            "publish_time": publish_time,
            "url": filing.filing_url,

            # SEC基础字段
            "ticker": filing.ticker,
            "cik": filing.cik,
            "company_name": filing.company_name,
            "form_type": filing.form_type,
            "accession_number": filing.accession_number,
            "filing_date": filing.filing_date,
            "report_date": filing.report_date,
            "acceptance_datetime": filing.acceptance_datetime,
            "primary_document": filing.primary_document,

            # SEC事件识别字段（新增）
            "items": items or [],
            "event_hint": event_hint,
            "pre_score": pre_score,
            "sec_rule_reason": sec_rule_reason,
            "risk_flags": risk_flags or [],

            # SEC附件字段（新增）
            "has_exhibits": bool(exhibits),
            "exhibit_count": len(exhibits) if exhibits else 0,
            "exhibits": exhibits or []
        }

        return normalized

    @staticmethod
    def _generate_title(filing: FilingMetadata) -> str:
        """
        生成title

        Args:
            filing: Filing元数据

        Returns:
            title

        Examples:
            >>> _generate_title(...)
            'NVDA 8-K 2024-12-31: Current Report'
        """
        # 基础格式：{ticker} {form} {filing_date}
        title = f"{filing.ticker} {filing.form_type} {filing.filing_date}"

        # 如果有公司名，添加
        if filing.company_name:
            title += f" - {filing.company_name}"

        return title

    @staticmethod
    def _parse_publish_time(filing: FilingMetadata) -> datetime:
        """
        解析发布时间

        Args:
            filing: Filing元数据

        Returns:
            datetime对象
        """
        # 优先使用acceptance_datetime
        if filing.acceptance_datetime:
            try:
                # ISO格式: 2024-12-31T16:30:00.000Z
                return datetime.fromisoformat(filing.acceptance_datetime.replace('Z', '+00:00'))
            except:
                pass

        # 使用filing_date
        try:
            return datetime.strptime(filing.filing_date, "%Y-%m-%d")
        except:
            return datetime.now()

    @staticmethod
    def to_raw_news_format(
        filing: FilingMetadata,
        content: str,
        items: list = None,
        event_hint: str = "",
        pre_score: int = 0,
        risk_flags: list = None,
        exhibits: list = None
    ) -> Dict[str, Any]:
        """
        转换为raw_news表格式（如果复用raw_news表）

        Args:
            filing: Filing元数据
            content: Filing正文
            items: 8-K Item列表
            event_hint: 事件类型提示
            pre_score: SEC规则预评分
            risk_flags: 风险标记
            exhibits: Exhibit列表

        Returns:
            raw_news表格式
        """
        import json

        normalized = FilingNormalizer.normalize(
            filing, content, items, event_hint,
            pre_score, "", risk_flags, exhibits
        )

        # raw_data包含所有SEC特有字段
        raw_data = {
            "ticker": filing.ticker,
            "cik": filing.cik,
            "company_name": filing.company_name,
            "form_type": filing.form_type,
            "accession_number": filing.accession_number,
            "filing_date": filing.filing_date,
            "report_date": filing.report_date,
            "acceptance_datetime": filing.acceptance_datetime,
            "primary_document": filing.primary_document,
            "items": items or [],
            "event_hint": event_hint,
            "pre_score": pre_score,
            "risk_flags": risk_flags or [],
            "has_exhibits": bool(exhibits),
            "exhibit_count": len(exhibits) if exhibits else 0
        }

        return {
            "news_id": normalized["news_id"],
            "source": normalized["source"],
            "title": normalized["title"],
            "content": normalized["content"],
            "publish_time": normalized["publish_time"],
            "url": normalized["url"],
            "raw_data": json.dumps(raw_data, ensure_ascii=False)
        }


__all__ = ['FilingNormalizer']
