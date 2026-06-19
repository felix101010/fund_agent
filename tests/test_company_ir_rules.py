"""
测试Company IR规则分类（增强版）
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestIRRulesEnhanced:
    """测试IR规则分类器（增强版）"""

    def test_earnings_release(self):
        """测试财报新闻稿"""
        rules = IRRules()
        item = {
            'title': 'NVIDIA Announces Financial Results for Second Quarter Fiscal 2027',
            'content': 'Revenue was $30 billion, diluted EPS was $2.50',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['document_type'] == 'earnings_release'
        assert result['event_hint'] == 'earnings_release'
        assert result['pre_score'] == 90
        assert result['need_ai'] is True

    def test_product_ramp(self):
        """测试产品量产"""
        rules = IRRules()
        item = {
            'title': 'NVIDIA Vera Rubin Ramps Into Full Production for Next-Gen AI',
            'content': 'Blackwell architecture reaches full production milestone',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['event_hint'] == 'product_ramp'
        assert result['pre_score'] == 85
        assert result['need_ai'] is True

    def test_supply_chain_partnership(self):
        """测试供应链合作"""
        rules = IRRules()
        item = {
            'title': 'NVIDIA and SK hynix Announce Multiyear Technology Partnership for HBM',
            'content': 'SK hynix will supply advanced HBM memory for NVIDIA GPUs',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['event_hint'] == 'supply_chain_partnership'
        assert result['pre_score'] == 85
        assert result['need_ai'] is True

    def test_ai_infrastructure(self):
        """测试AI基础设施"""
        rules = IRRules()
        item = {
            'title': 'SK Telecom and NVIDIA Build AI Infrastructure for Sovereign AI',
            'content': 'Partnership to build AI factory and data center infrastructure',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['event_hint'] == 'ai_infrastructure'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_strategic_partnership(self):
        """测试战略合作"""
        rules = IRRules()
        item = {
            'title': 'NVIDIA and Microsoft Announce Multiyear Collaboration on AI',
            'content': 'The companies will collaborate on cloud AI infrastructure',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['event_hint'] == 'strategic_partnership'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_low_value_geforce(self):
        """测试低价值GeForce新闻"""
        rules = IRRules()
        item = {
            'title': 'GeForce NOW Summer Sale: New Games Join the Service',
            'content': 'Gaming community can enjoy new titles on GeForce NOW',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['event_hint'] == 'low_value_company_news'
        assert result['pre_score'] == 30
        assert result['need_ai'] is False

    def test_low_value_stockholder(self):
        """测试低价值股东会议"""
        rules = IRRules()
        item = {
            'title': 'Stockholder Meeting Set for Annual Meeting',
            'content': 'Stockholders can participate online at the annual meeting',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['event_hint'] == 'low_value_company_news'
        assert result['pre_score'] == 30
        assert result['need_ai'] is False

    def test_capital_return(self):
        """测试股东回报"""
        rules = IRRules()
        item = {
            'title': 'NVIDIA Announces Dividend and Share Repurchase Program',
            'content': 'The company will increase quarterly dividend and authorize buyback',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['document_type'] == 'capital_return'
        assert result['event_hint'] == 'capital_return'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_earnings_event_notice(self):
        """测试财报日期预告"""
        rules = IRRules()
        item = {
            'title': 'NVIDIA will release financial results on January 15',
            'content': 'The company will host a conference call to discuss results',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['document_type'] == 'earnings_event_notice'
        assert result['event_hint'] == 'earnings_date_announcement'
        assert result['pre_score'] == 65
        # 财报预告不需要AI（只是日期通知）
        assert result['need_ai'] is False

    def test_default_classification(self):
        """测试默认分类"""
        rules = IRRules()
        item = {
            'title': 'NVIDIA News Update',
            'content': 'Some general company news',
            'summary': ''
        }
        result = rules.classify(item)
        
        assert result['document_type'] == 'press_release'
        assert result['event_hint'] == 'company_news'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False  # <65分


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
