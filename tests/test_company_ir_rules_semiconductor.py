"""
测试半导体公司IR规则
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestSemiconductorRules:
    """测试半导体公司专属规则"""

    def test_marvell_cfo_transition(self):
        """测试Marvell CFO Transition"""
        rules = IRRules()
        item = {
            'ticker': 'MRVL',
            'title': 'Marvell Announces CFO Transition',
            'content': 'Chief Financial Officer transition effective next quarter',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'executive_change'
        assert result['pre_score'] >= 75
        assert result['need_ai'] is True

    def test_marvell_102tbps_switch(self):
        """测试Marvell 102.4 Tbps Switch"""
        rules = IRRules()
        item = {
            'ticker': 'MRVL',
            'title': "Marvell Announces Availability of Industry's First 102.4 Tbps Switch Purpose-Built for AI and Cloud Data Center Infrastructure",
            'content': 'Purpose-built for AI data center scale-up infrastructure',
            'summary': ''
        }
        result = rules.classify(item)

        # 应该是 product_launch 或 ai_infrastructure
        assert result['event_hint'] in ['product_launch', 'ai_infrastructure']
        assert result['pre_score'] >= 80
        assert result['need_ai'] is True

    def test_marvell_pcie60_switch(self):
        """测试Marvell PCIe 6.0 Switch"""
        rules = IRRules()
        item = {
            'ticker': 'MRVL',
            'title': "Marvell Launches Industry's First 260-lane PCIe 6.0 Switch for AI Data Center Scale-up Infrastructure",
            'content': 'PCIe 6.0 switch for connectivity and scale-up infrastructure',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] in ['product_launch', 'ai_infrastructure']
        assert result['pre_score'] >= 80
        assert result['need_ai'] is True

    def test_intel_to_report_earnings(self):
        """测试Intel财报预告"""
        rules = IRRules()
        item = {
            'ticker': 'INTC',
            'title': 'Intel to Report First-Quarter 2026 Financial Results',
            'content': 'The company will host a conference call to discuss results',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'earnings_date_announcement'
        assert result['document_type'] == 'earnings_event_notice'
        assert result['pre_score'] == 65
        # 财报预告不需要AI
        assert result['need_ai'] is False

    def test_intel_reports_earnings(self):
        """测试Intel正式财报"""
        rules = IRRules()
        item = {
            'ticker': 'INTC',
            'title': 'Intel Reports First-Quarter 2026 Financial Results',
            'content': 'Revenue was $12.7 billion, operating income of $2.1 billion',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'earnings_release'
        assert result['document_type'] == 'earnings_release'
        assert result['pre_score'] == 90
        assert result['need_ai'] is True

    def test_lam_quarterly_dividend(self):
        """测试Lam Research普通季度分红"""
        rules = IRRules()
        item = {
            'ticker': 'LRCX',
            'title': 'Lam Research Corporation Declares Quarterly Dividend',
            'content': 'Regular quarterly dividend payment to shareholders',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'regular_dividend'
        assert result['pre_score'] == 60
        assert result['need_ai'] is False

    def test_marvell_quarterly_dividend(self):
        """测试Marvell普通季度分红"""
        rules = IRRules()
        item = {
            'ticker': 'MRVL',
            'title': 'Marvell Declares Quarterly Dividend Payment',
            'content': 'The company declares regular quarterly dividend',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'regular_dividend'
        assert result['pre_score'] == 60
        assert result['need_ai'] is False

    def test_special_dividend(self):
        """测试特殊分红（应该需要AI）"""
        rules = IRRules()
        item = {
            'ticker': 'INTC',
            'title': 'Intel Announces Special Dividend and Share Repurchase Program',
            'content': 'The company will increase dividend and authorize buyback',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'capital_return'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_board_chair_retirement_not_executive_change(self):
        """测试Board Chair退休不应该算高管变动"""
        rules = IRRules()
        item = {
            'ticker': 'INTC',
            'title': 'Intel Board Chair Frank D. Yeary to Retire Following Annual Meeting',
            'content': 'Board chair will retire, not a CEO or CFO change',
            'summary': ''
        }
        result = rules.classify(item)

        # 不应该是 executive_change
        assert result['event_hint'] != 'executive_change'
        # 应该是普通公司新闻
        assert result['pre_score'] <= 50

    def test_cxl_switch_announcement(self):
        """测试CXL Switch公告"""
        rules = IRRules()
        item = {
            'ticker': 'MRVL',
            'title': 'Marvell Unveils CXL 3.0 Switch for Memory Pooling',
            'content': 'CXL switch enables memory pooling and AI memory wall solutions',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] in ['product_launch', 'ai_infrastructure']
        assert result['pre_score'] >= 80
        assert result['need_ai'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
