"""
测试GOOGL规则
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestGoogleRules:
    """测试Google公司专属规则"""

    def test_alabama_data_center_investment(self):
        """测试Alabama数据中心投资"""
        rules = IRRules()
        item = {
            'ticker': 'GOOGL',
            'title': "We're strengthening our presence in Alabama through new investments and data centers",
            'content': 'Google is investing in cloud infrastructure and creating jobs in Alabama with new data center investments',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_infrastructure'
        assert result['document_type'] == 'ai_infrastructure'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_gemini_tools_for_business(self):
        """测试Gemini工具发布"""
        rules = IRRules()
        item = {
            'ticker': 'GOOGL',
            'title': 'Save time and grow your business with new Gemini tools',
            'content': 'New AI capabilities in Gemini to help businesses',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_product_update'
        assert result['document_type'] == 'ai_product_update'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_diffusion_gemma_model(self):
        """测试DiffusionGemma模型发布"""
        rules = IRRules()
        item = {
            'ticker': 'GOOGL',
            'title': 'DiffusionGemma: 4x faster text generation',
            'content': 'Open model release with improved performance',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_model_update'
        assert result['document_type'] == 'ai_model_update'
        assert result['pre_score'] == 65
        assert result['need_ai'] is False

    def test_walmart_connect_partnership(self):
        """测试Walmart Connect广告合作"""
        rules = IRRules()
        item = {
            'ticker': 'GOOGL',
            'title': "We're bringing Walmart Connect to Display & Video 360",
            'content': 'Strategic partnership for marketing platform and ads',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'strategic_partnership'
        assert result['document_type'] == 'strategic_partnership'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_commencement_address(self):
        """测试毕业演讲"""
        rules = IRRules()
        item = {
            'ticker': 'GOOGL',
            'title': "Read Sundar Pichai's 2026 Commencement Address",
            'content': 'CEO speech to students about future',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'company_news'
        assert result['document_type'] == 'company_news'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_notebooklm_ai_product(self):
        """测试NotebookLM AI产品"""
        rules = IRRules()
        item = {
            'ticker': 'GOOGL',
            'title': 'NotebookLM gets new AI features',
            'content': 'Google AI Studio and Workspace AI enhancements',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_product_update'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_digital_literacy_education(self):
        """测试数字素养教育项目"""
        rules = IRRules()
        item = {
            'ticker': 'GOOGL',
            'title': 'Helping parents and students with digital literacy',
            'content': 'Education program for families and culture report',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'company_news'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_google_cloud_tpu_infrastructure(self):
        """测试Google Cloud TPU基础设施"""
        rules = IRRules()
        item = {
            'ticker': 'GOOGL',
            'title': 'Google Cloud expands TPU capacity with new data centers',
            'content': 'AI infrastructure investment in cloud regions with TPU and AI capacity',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_infrastructure'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
