"""
测试Company IR配置
"""
import pytest

from fund_quant.data_sources.news.company_ir import (
    get_ir_company_config,
    list_enabled_ir_tickers
)


class TestIRCompanyConfig:
    """测试IR公司配置"""

    def test_list_enabled_ir_tickers(self):
        """测试列出启用的tickers"""
        tickers = list_enabled_ir_tickers()

        # 应该包含4家公司
        assert len(tickers) >= 4
        assert 'NVDA' in tickers
        assert 'TSLA' in tickers
        assert 'AAPL' in tickers
        assert 'MSFT' in tickers

    def test_get_ir_company_config_nvda(self):
        """测试获取NVDA配置"""
        config = get_ir_company_config('NVDA')

        assert config is not None
        assert config['company_name'] == 'NVIDIA'
        assert config['enabled'] is True
        assert 'ir_home' in config

    def test_get_ir_company_config_lowercase(self):
        """测试小写ticker"""
        config = get_ir_company_config('nvda')

        assert config is not None
        assert config['company_name'] == 'NVIDIA'

    def test_get_ir_company_config_tsla(self):
        """测试获取TSLA配置"""
        config = get_ir_company_config('TSLA')

        assert config is not None
        assert config['company_name'] == 'Tesla'

    def test_get_ir_company_config_not_exist(self):
        """测试不存在的公司"""
        config = get_ir_company_config('INVALID')

        assert config is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
