"""
测试财报预告规则
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestEarningsNoticeRules:
    """测试财报预告规则"""

    def test_lrcx_conference_call_notice(self):
        """测试LRCX财报电话会议预告"""
        rules = IRRules()
        item = {
            'ticker': 'LRCX',
            'title': 'Lam Research Corporation Announces March Quarter Financial Conference Call',
            'content': 'The company will host a conference call to review financial results',
            'summary': ''
        }
        result = rules.classify(item)

        # 应该是 earnings_date_announcement
        assert result['event_hint'] == 'earnings_date_announcement'
        assert result['need_ai'] is False

    def test_intel_to_report_earnings_simple(self):
        """测试Intel普通财报预告"""
        rules = IRRules()
        item = {
            'ticker': 'INTC',
            'title': 'Intel to Report First-Quarter 2026 Financial Results',
            'content': 'The company will report financial results on April 24',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'earnings_date_announcement'
        assert result['document_type'] == 'earnings_event_notice'
        assert result['pre_score'] == 65
        # 没有guidance，不需要AI
        assert result['need_ai'] is False

    def test_intel_earnings_with_guidance(self):
        """测试Intel财报预告+guidance更新"""
        rules = IRRules()
        item = {
            'ticker': 'INTC',
            'title': 'Intel to Report Q1 Results and Updated Guidance',
            'content': 'Intel will report financial results and provide updated guidance for Q2',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'earnings_date_announcement'
        assert result['pre_score'] == 65
        # 包含 updated guidance，需要AI
        assert result['need_ai'] is True

    def test_earnings_preannouncement_with_warning(self):
        """测试财报预警"""
        rules = IRRules()
        item = {
            'ticker': 'INTC',
            'title': 'Intel Warns on Q1 Revenue; Lowers Guidance',
            'content': 'Intel warns that Q1 revenue will be below expectations and lowers guidance',
            'summary': ''
        }
        result = rules.classify(item)

        # warns/lowers guidance 应该是高价值事件，需要AI
        # 可能被识别为 earnings_release 或 business_update
        assert result['pre_score'] >= 75
        assert result['need_ai'] is True

    def test_earnings_preliminary_results(self):
        """测试初步财报结果"""
        rules = IRRules()
        item = {
            'ticker': 'NVDA',
            'title': 'NVIDIA Announces Preliminary Results for Q1',
            'content': 'NVIDIA announces preliminary financial results showing strong revenue',
            'summary': ''
        }
        result = rules.classify(item)

        # preliminary results 应该是高价值事件，需要AI
        # 可能被识别为 earnings_release 或 business_update
        assert result['pre_score'] >= 75
        assert result['need_ai'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
