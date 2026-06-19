"""
测试AAPL专属规则
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestAAPLRules:
    """测试AAPL公司专属规则"""

    def test_apple_intelligence(self):
        """测试Apple Intelligence分类"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple Announces Apple Intelligence',
            'content': 'New AI capabilities with on-device intelligence and Private Cloud Compute',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_product_update'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_siri_ai(self):
        """测试Siri AI分类"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple Unveils Next-Generation Siri AI',
            'content': 'Enhanced intelligence experiences across iOS',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_product_update'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_dma_delay(self):
        """测试DMA延期分类"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple Intelligence and Siri AI Delayed in EU Due to DMA',
            'content': 'iOS and iPadOS features delayed in European Union due to regulation',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'regulatory_product_delay'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_app_store_metrics(self):
        """测试App Store指标分类"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'App Store Ecosystem Reaches $1.4 Trillion',
            'content': 'Developers thrive with billions in transactions, fraudulent transactions blocked',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'business_metric_update'
        assert result['pre_score'] == 70
        assert result['need_ai'] is True

    def test_developer_academy_low_value(self):
        """测试Developer Academy低价值分类"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple Developer Academy Welcomes Rising Developers',
            'content': 'Students and community members join education program',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'developer_ecosystem'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_developer_academy_with_high_value_keyword(self):
        """测试Developer Academy但包含高价值关键词时不降级"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple Developer Academy: App Store Ecosystem Impact',
            'content': 'Revenue and acquisition from Academy graduates',
            'summary': ''
        }
        result = rules.classify(item)

        # 包含App Store ecosystem，应该被business_metric_update规则捕获
        assert result['event_hint'] == 'business_metric_update'
        assert result['pre_score'] == 70


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
