"""
SEC EDGAR 采集器单元测试
"""
import pytest
from fund_quant.data_sources.sec_edgar.ticker_mapper import TickerMapper
from fund_quant.data_sources.sec_edgar.filing_collector import FilingCollector


def test_pad_cik_10_digits():
    """测试CIK补齐10位"""
    assert TickerMapper.pad_cik("1045810") == "0001045810"
    assert TickerMapper.pad_cik("320193") == "0000320193"
    assert TickerMapper.pad_cik("0001045810") == "0001045810"
    print("✅ CIK补齐测试通过")


def test_remove_cik_leading_zeros():
    """测试移除CIK前导零"""
    assert TickerMapper.remove_cik_leading_zeros("0001045810") == "1045810"
    assert TickerMapper.remove_cik_leading_zeros("0000320193") == "320193"
    print("✅ CIK前导零移除测试通过")


def test_remove_accession_dashes():
    """测试移除accession number横线"""
    accession = "0001045810-24-000123"
    expected = "000104581024000123"
    assert accession.replace("-", "") == expected
    print("✅ Accession横线移除测试通过")


def test_build_archives_url():
    """测试构建Archives URL"""
    collector = FilingCollector()

    cik = "0001045810"
    accession = "0001045810-24-000123"
    doc = "nvda-20241231.htm"

    url = collector._build_filing_url(cik, accession, doc)

    assert "edgar/data/1045810" in url
    assert "000104581024000123" in url
    assert "nvda-20241231.htm" in url

    print(f"✅ URL构建测试通过")
    print(f"   {url}")


def test_filter_8k_forms():
    """测试8-K过滤"""
    forms = ["8-K", "10-Q", "8-K/A", "10-K"]
    target_forms = ["8-K", "8-K/A"]

    filtered = [f for f in forms if f in target_forms]

    assert filtered == ["8-K", "8-K/A"]
    print("✅ 8-K过滤测试通过")


def test_html_to_text():
    """测试HTML转文本"""
    from fund_quant.data_sources.sec_edgar.filing_downloader import FilingDownloader

    downloader = FilingDownloader()

    html = """
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Item 1.01 Entry into Material Agreement</h1>
        <p>The Company entered into a definitive agreement.</p>
        <script>alert('test');</script>
    </body>
    </html>
    """

    text = downloader._clean_html(html)

    assert "Item 1.01" in text
    assert "definitive agreement" in text
    assert "alert" not in text  # script应该被移除
    assert "<html>" not in text  # HTML标签应该被移除

    print("✅ HTML清洗测试通过")


if __name__ == "__main__":
    test_pad_cik_10_digits()
    test_remove_cik_leading_zeros()
    test_remove_accession_dashes()
    test_build_archives_url()
    test_filter_8k_forms()
    test_html_to_text()

    print("\n🎉 所有测试通过！")
