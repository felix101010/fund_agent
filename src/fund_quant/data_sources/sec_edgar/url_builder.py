"""
URL构建器
统一构建SEC各种URL
"""


class SECURLBuilder:
    """
    SEC URL构建器

    职责：
    统一构建submissions URL、primary document URL、index.json URL
    """

    SEC_DATA_BASE = "https://data.sec.gov"
    SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"

    @staticmethod
    def build_submissions_url(cik: str) -> str:
        """
        构建submissions URL

        Args:
            cik: CIK（10位）

        Returns:
            submissions URL

        Examples:
            >>> SECURLBuilder.build_submissions_url("0001045810")
            'https://data.sec.gov/submissions/CIK0001045810.json'
        """
        return f"{SECURLBuilder.SEC_DATA_BASE}/submissions/CIK{cik}.json"

    @staticmethod
    def build_primary_document_url(cik: str, accession_number: str, primary_document: str) -> str:
        """
        构建primary document URL

        Args:
            cik: CIK（10位）
            accession_number: Accession number（带横线）
            primary_document: 主文档名

        Returns:
            primary document URL

        Examples:
            >>> SECURLBuilder.build_primary_document_url(
            ...     "0001045810",
            ...     "0001045810-24-000123",
            ...     "nvda-20241231.htm"
            ... )
            'https://www.sec.gov/Archives/edgar/data/1045810/000104581024000123/nvda-20241231.htm'
        """
        # 移除CIK前导零
        cik_no_zeros = str(int(cik))

        # 移除accession number横线
        accession_no_dash = accession_number.replace("-", "")

        # 拼接URL
        url = f"{SECURLBuilder.SEC_ARCHIVES_BASE}/{cik_no_zeros}/{accession_no_dash}/{primary_document}"

        return url

    @staticmethod
    def build_index_json_url(cik: str, accession_number: str) -> str:
        """
        构建index.json URL（用于获取附件列表）

        Args:
            cik: CIK（10位）
            accession_number: Accession number（带横线）

        Returns:
            index.json URL

        Examples:
            >>> SECURLBuilder.build_index_json_url("0001045810", "0001045810-24-000123")
            'https://www.sec.gov/Archives/edgar/data/1045810/000104581024000123/index.json'
        """
        # 移除CIK前导零
        cik_no_zeros = str(int(cik))

        # 移除accession number横线
        accession_no_dash = accession_number.replace("-", "")

        # 拼接URL
        url = f"{SECURLBuilder.SEC_ARCHIVES_BASE}/{cik_no_zeros}/{accession_no_dash}/index.json"

        return url

    @staticmethod
    def build_exhibit_url(cik: str, accession_number: str, filename: str) -> str:
        """
        构建exhibit URL

        Args:
            cik: CIK（10位）
            accession_number: Accession number（带横线）
            filename: 附件文件名

        Returns:
            exhibit URL

        Examples:
            >>> SECURLBuilder.build_exhibit_url(
            ...     "0001045810",
            ...     "0001045810-24-000123",
            ...     "ex991.htm"
            ... )
            'https://www.sec.gov/Archives/edgar/data/1045810/000104581024000123/ex991.htm'
        """
        # 移除CIK前导零
        cik_no_zeros = str(int(cik))

        # 移除accession number横线
        accession_no_dash = accession_number.replace("-", "")

        # 拼接URL
        url = f"{SECURLBuilder.SEC_ARCHIVES_BASE}/{cik_no_zeros}/{accession_no_dash}/{filename}"

        return url


__all__ = ['SECURLBuilder']
