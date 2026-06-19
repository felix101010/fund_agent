"""
测试KLAC规则
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestKLACRules:
    """测试KLAC公司专属规则"""

    def test_klac_stock_split_with_dividend(self):
        """测试KLAC股票分割+分红公告"""
        rules = IRRules()
        item = {
            'ticker': 'KLAC',
            'title': 'KLA Corporation Announces Ten-to-One Stock Split and Quarterly Cash Dividend',
            'content': 'The company will implement a 10-for-1 forward stock split and declares quarterly dividend',
            'summary': ''
        }
        result = rules.classify(item)

        # stock_split 优先级高于 regular_dividend
        assert result['event_hint'] == 'stock_split'
        assert result['document_type'] == 'stock_split'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_klac_investor_day_webcast_details(self):
        """测试KLAC投资者日Webcast预告"""
        rules = IRRules()
        item = {
            'ticker': 'KLAC',
            'title': 'KLA Announces Webcast Details for Upcoming Investor Day',
            'content': 'The company will host a webcast for the upcoming investor day event',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'investor_event_notice'
        assert result['document_type'] == 'investor_event_notice'
        assert result['pre_score'] == 60
        assert result['need_ai'] is False

    def test_klac_investor_day_with_buyback(self):
        """测试KLAC投资者日+回购计划公告"""
        rules = IRRules()
        item = {
            'ticker': 'KLAC',
            'title': 'KLA Hosts Investor Day; Announces $7 Billion Share Repurchase Program',
            'content': 'At its investor day, KLA announced a new $7 billion share buyback authorization',
            'summary': ''
        }
        result = rules.classify(item)

        # 包含 share repurchase，应该是高价值的 capital_return 或 business_update
        assert result['event_hint'] in ['capital_return', 'business_update']
        assert result['pre_score'] >= 75
        assert result['need_ai'] is True

    def test_klac_participate_in_conferences(self):
        """测试KLAC参加投资者会议预告"""
        rules = IRRules()
        item = {
            'ticker': 'KLAC',
            'title': 'KLA to Participate in Upcoming Investor Conferences',
            'content': 'The company will participate in several investor conferences in Q2',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'investor_event_notice'
        assert result['pre_score'] == 60
        assert result['need_ai'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
