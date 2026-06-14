"""
Filing 采集器
解析submissions JSON，筛选和过滤filings
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from fund_quant.data_sources.sec_edgar.sec_client import SECClient
from fund_quant.data_sources.sec_edgar.ticker_mapper import TickerMapper


@dataclass
class FilingMetadata:
    """Filing元数据"""
    filing_id: str  # sec_{ticker}_{accessionNumber}
    ticker: str
    cik: str  # 10位CIK
    company_name: str
    form_type: str
    accession_number: str  # 原始格式（带横线）
    filing_date: str  # YYYY-MM-DD
    report_date: Optional[str]  # YYYY-MM-DD
    acceptance_datetime: Optional[str]  # ISO格式
    primary_document: str
    filing_url: str
    is_new: bool = True  # 是否为新filing


class FilingCollector:
    """
    Filing 采集器

    职责：
    1. 获取submissions
    2. 筛选表单类型
    3. since_date过滤
    4. 生成filing_id和URL
    5. 去重检查
    """

    def __init__(self, sec_client: SECClient = None, ticker_mapper: TickerMapper = None):
        """
        初始化

        Args:
            sec_client: SEC客户端
            ticker_mapper: Ticker映射器
        """
        self.sec_client = sec_client or SECClient()
        self.ticker_mapper = ticker_mapper or TickerMapper()

    def collect_filings(
        self,
        tickers: List[str],
        forms: List[str] = None,
        since_date: str = None,
        days: int = None,
        max_filings_per_ticker: int = 100
    ) -> List[FilingMetadata]:
        """
        采集filings

        Args:
            tickers: 股票代码列表
            forms: 表单类型列表（默认["8-K"]）
            since_date: 起始日期 YYYY-MM-DD
            days: 最近N天（与since_date二选一）
            max_filings_per_ticker: 每个ticker最大filings数

        Returns:
            List[FilingMetadata]
        """
        if forms is None:
            forms = ["8-K", "8-K/A"]

        # 计算since_date
        if days:
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        all_filings = []

        for ticker in tickers:
            # 获取CIK
            cik = self.ticker_mapper.get_cik(ticker)
            if not cik:
                print(f"⚠️  未找到{ticker}的CIK")
                continue

            # 获取submissions
            submissions = self.sec_client.get_submissions(cik)
            if not submissions:
                print(f"⚠️  获取{ticker} submissions失败")
                continue

            # 解析filings
            filings = self._parse_submissions(
                ticker=ticker,
                cik=cik,
                submissions=submissions,
                forms=forms,
                since_date=since_date,
                max_filings=max_filings_per_ticker
            )

            all_filings.extend(filings)

        return all_filings

    def _parse_submissions(
        self,
        ticker: str,
        cik: str,
        submissions: Dict[str, Any],
        forms: List[str],
        since_date: Optional[str],
        max_filings: int
    ) -> List[FilingMetadata]:
        """
        解析submissions JSON

        Args:
            ticker: 股票代码
            cik: CIK
            submissions: submissions JSON
            forms: 表单类型列表
            since_date: 起始日期
            max_filings: 最大filings数

        Returns:
            List[FilingMetadata]
        """
        filings = []
        company_name = submissions.get('name', '')

        recent = submissions.get('filings', {}).get('recent', {})
        if not recent:
            return filings

        # 获取字段数组
        accession_numbers = recent.get('accessionNumber', [])
        form_types = recent.get('form', [])
        filing_dates = recent.get('filingDate', [])
        report_dates = recent.get('reportDate', [])
        primary_documents = recent.get('primaryDocument', [])
        acceptance_datetimes = recent.get('acceptanceDateTime', [])

        # 遍历filings
        for i in range(len(accession_numbers)):
            form_type = form_types[i]
            filing_date = filing_dates[i]

            # 过滤表单类型
            if form_type not in forms:
                continue

            # 过滤日期
            if since_date and filing_date < since_date:
                continue

            # 生成filing_id
            accession_number = accession_numbers[i]
            filing_id = self._generate_filing_id(ticker, accession_number)

            # 生成filing_url
            filing_url = self._build_filing_url(
                cik=cik,
                accession_number=accession_number,
                primary_document=primary_documents[i]
            )

            # 创建元数据
            filing = FilingMetadata(
                filing_id=filing_id,
                ticker=ticker,
                cik=cik,
                company_name=company_name,
                form_type=form_type,
                accession_number=accession_number,
                filing_date=filing_date,
                report_date=report_dates[i] if i < len(report_dates) else None,
                acceptance_datetime=acceptance_datetimes[i] if i < len(acceptance_datetimes) else None,
                primary_document=primary_documents[i],
                filing_url=filing_url
            )

            filings.append(filing)

            # 限制数量
            if len(filings) >= max_filings:
                break

        return filings

    def _generate_filing_id(self, ticker: str, accession_number: str) -> str:
        """
        生成filing_id

        Args:
            ticker: 股票代码
            accession_number: accession number

        Returns:
            filing_id

        Examples:
            >>> _generate_filing_id("NVDA", "0001045810-24-000123")
            'sec_NVDA_0001045810-24-000123'
        """
        return f"sec_{ticker}_{accession_number}"

    def _build_filing_url(self, cik: str, accession_number: str, primary_document: str) -> str:
        """
        构建filing URL

        Args:
            cik: CIK（10位）
            accession_number: accession number（带横线）
            primary_document: 主文档名

        Returns:
            filing URL

        Examples:
            >>> _build_filing_url("0001045810", "0001045810-24-000123", "nvda-20241231.htm")
            'https://www.sec.gov/Archives/edgar/data/1045810/000104581024000123/nvda-20241231.htm'
        """
        # 移除CIK前导零
        cik_no_zeros = str(int(cik))

        # 移除accession number横线
        accession_no_dash = accession_number.replace("-", "")

        # 拼接URL
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_no_dash}/{primary_document}"

        return url


__all__ = ['FilingMetadata', 'FilingCollector']
