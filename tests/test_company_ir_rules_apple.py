"""
测试AAPL规则
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestAppleRules:
    """测试Apple公司专属规则"""

    def test_apple_intelligence_announcement(self):
        """测试Apple Intelligence公告"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple unveils next generation of Apple Intelligence, Siri AI, and more',
            'content': 'Apple announces new Apple Intelligence features with enhanced on-device intelligence',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_product_update'
        assert result['document_type'] == 'ai_product_update'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_dma_siri_delay(self):
        """测试DMA导致Siri AI延迟"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Due to DMA, Siri AI delayed in EU for iOS 27 and iPadOS 27',
            'content': 'European Union regulation requires changes to Apple Intelligence rollout',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'regulatory_product_delay'
        assert result['document_type'] == 'regulatory_product_delay'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_app_store_ecosystem(self):
        """测试App Store生态系统指标"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'App Store ecosystem reaches $1.4 trillion as developers thrive globally',
            'content': 'The App Store ecosystem stopped over $7 billion in fraudulent transactions',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'business_metric_update'
        assert result['document_type'] == 'business_metric_update'
        assert result['pre_score'] == 70
        assert result['need_ai'] is True

    def test_apple_sports_expansion(self):
        """测试Apple Sports扩展"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple Sports expands to more than 90 new countries and regions',
            'content': 'Apple Sports now available in over 90 countries',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'content_service_update'
        assert result['document_type'] == 'content_service_update'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_mlb_friday_night_baseball(self):
        """测试Major League Baseball公告"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple and Major League Baseball announce July Friday Night Baseball schedule',
            'content': 'Live pro sports streaming on Apple TV',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'content_service_update'
        assert result['document_type'] == 'content_service_update'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_apple_arcade_game(self):
        """测试Apple Arcade游戏发布"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple Arcade adds Mini Football and Family Feud',
            'content': 'New games available on Apple Arcade',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'content_service_update'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_developer_academy(self):
        """测试Developer Academy"""
        rules = IRRules()
        item = {
            'ticker': 'AAPL',
            'title': 'Apple Developer Academy celebrates rising developers',
            'content': 'Education program for students and community',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'developer_ecosystem'
        assert result['document_type'] == 'developer_ecosystem'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
