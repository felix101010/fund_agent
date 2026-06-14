"""
SEC EDGAR 数据源模块

从SEC EDGAR获取美股公司filings（8-K/10-Q/10-K等）

遵守SEC Fair Access规则：
- 请求频率不超过10 req/s
- 默认2 req/s
- 必须设置User-Agent（含邮箱）

法律说明：
- 使用SEC官方免费数据源
- 遵守SEC Fair Access规则
- 仅用于个人研究和技术学习
"""
from fund_quant.data_sources.sec_edgar.ticker_mapper import TickerMapper
from fund_quant.data_sources.sec_edgar.sec_client import SECClient
from fund_quant.data_sources.sec_edgar.filing_collector import FilingCollector, FilingMetadata
from fund_quant.data_sources.sec_edgar.filing_downloader import FilingDownloader
from fund_quant.data_sources.sec_edgar.filing_normalizer import FilingNormalizer

__all__ = [
    'TickerMapper',
    'SECClient',
    'FilingCollector',
    'FilingMetadata',
    'FilingDownloader',
    'FilingNormalizer'
]
