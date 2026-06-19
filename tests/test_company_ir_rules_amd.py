"""
测试AMD规则
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestAMDRules:
    """测试AMD公司专属规则"""

    def test_amd_uk_ai_investment(self):
        """测试AMD英国AI投资"""
        rules = IRRules()
        item = {
            'ticker': 'AMD',
            'title': 'AMD Commits up to £2 Billion to Accelerate AI Innovation and Research in the UK',
            'content': 'AMD investment in AI research and innovation in the United Kingdom',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_investment'
        assert result['document_type'] == 'ai_investment'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_amd_taiwan_ecosystem_investment(self):
        """测试AMD台湾生态系统投资"""
        rules = IRRules()
        item = {
            'ticker': 'AMD',
            'title': 'AMD Announces More Than $10 Billion in Taiwan Ecosystem Investments',
            'content': 'More than $10 billion investment in Taiwan AI ecosystem and supply chain',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'supply_chain_investment'
        assert result['document_type'] == 'supply_chain_investment'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_amd_earnings_date_announcement(self):
        """测试AMD财报日期公告"""
        rules = IRRules()
        item = {
            'ticker': 'AMD',
            'title': 'AMD to Report Fiscal First Quarter 2026 Financial Results',
            'content': 'AMD will report financial results and host conference call to review',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'earnings_date_announcement'
        assert result['document_type'] == 'earnings_event_notice'
        assert result['pre_score'] == 65
        assert result['need_ai'] is False

    def test_amd_advancing_ai_event(self):
        """测试AMD Advancing AI活动公告"""
        rules = IRRules()
        item = {
            'ticker': 'AMD',
            'title': 'AMD Announces Advancing AI 2026',
            'content': 'AMD AI event keynote and webcast details',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_event_notice'
        assert result['document_type'] == 'investor_event_notice'
        assert result['pre_score'] == 60
        assert result['need_ai'] is False

    def test_amd_ai_pc_ryzen(self):
        """测试AMD AI PC产品发布"""
        rules = IRRules()
        item = {
            'ticker': 'AMD',
            'title': 'AMD Gives Consumers and Businesses More AI PC Options with Expanded Ryzen',
            'content': 'Expanded Ryzen lineup with AI PC capabilities',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_pc_product_update'
        assert result['document_type'] == 'ai_pc_product_update'
        assert result['pre_score'] == 65
        assert result['need_ai'] is False

    def test_amd_regular_earnings_release(self):
        """测试AMD正式财报发布（应该仍然识别为earnings_release）"""
        rules = IRRules()
        item = {
            'ticker': 'AMD',
            'title': 'AMD Reports Fourth Quarter 2025 Financial Results',
            'content': 'Revenue was $7.3 billion, GAAP earnings per share, non-GAAP earnings',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'earnings_release'
        assert result['document_type'] == 'earnings_release'
        assert result['pre_score'] == 90
        assert result['need_ai'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
