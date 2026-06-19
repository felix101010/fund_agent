"""
测试META规则
"""
import pytest

from fund_quant.data_sources.news.company_ir import IRRules


class TestMetaRules:
    """测试META公司专属规则"""

    def test_threads_500m_users(self):
        """测试Threads 5亿用户公告"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'New Features to Celebrate 500 Million Monthly Users on Threads',
            'content': 'Threads reaches 500 million monthly active users milestone',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'social_app_update'
        assert result['document_type'] == 'social_app_update'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_facebook_ai_tools(self):
        """测试Facebook AI工具"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'New AI Tools to Help You Make Things Happen on Facebook',
            'content': 'Meta AI and generative AI tools for Facebook users',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_product_update'
        assert result['document_type'] == 'ai_product_update'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_ai_glasses_veterans(self):
        """测试AI眼镜项目"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'The Future Is for Everyone: Free AI Glasses for Every Blind Veteran in America',
            'content': 'Ray-Ban Meta smart glasses program for veterans',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'metaverse_hardware'
        assert result['document_type'] == 'metaverse_hardware'
        assert result['pre_score'] == 75
        assert result['need_ai'] is True

    def test_football_fans_meta_apps(self):
        """测试Meta Apps足球内容"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'Going All in for Global Football Fans Across Meta Apps',
            'content': 'Football content on Instagram and Facebook',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'social_app_update'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_social_media_bans_age_verification(self):
        """测试社交媒体禁令和年龄验证"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': "Why Social Media Bans Alone Can't Solve the Age Verification Dilemma",
            'content': 'Policy discussion on age verification and social media bans',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'regulatory_policy'
        assert result['document_type'] == 'regulatory_policy'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_infrastructure_compute_power(self):
        """测试基础设施解释器"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'Infrastructure Explained: Compute Power',
            'content': 'Explaining AI infrastructure and compute power for data centers',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_infrastructure'
        assert result['document_type'] == 'ai_infrastructure'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_reliance_data_center_partnership(self):
        """测试Reliance数据中心合作"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'Meta Partners With Reliance on AI-Enabled Data Center in India',
            'content': 'Strategic partnership for AI-enabled data center infrastructure',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'ai_infrastructure'
        assert result['document_type'] == 'ai_infrastructure'
        assert result['pre_score'] == 80
        assert result['need_ai'] is True

    def test_personalization_controls(self):
        """测试个性化和隐私控制"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'Better Personalization and Changes to Controls for Your Activity From Meta',
            'content': 'Privacy controls and data controls updates',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'privacy_policy_update'
        assert result['document_type'] == 'privacy_policy_update'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_workforce_academy(self):
        """测试员工培训学院"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': "America's Workforce Academy: The Future Is for Everyone",
            'content': 'Free skills training and education program for workforce',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'company_news'
        assert result['document_type'] == 'company_news'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False

    def test_whatsapp_spyware_security(self):
        """测试WhatsApp安全更新"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'Fighting Spyware: An Update From WhatsApp',
            'content': 'WhatsApp security update addressing spyware threats',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'security_update'
        assert result['document_type'] == 'security_update'
        assert result['pre_score'] == 60
        assert result['need_ai'] is False

    def test_community_standards_audit(self):
        """测试社区标准审计评论"""
        rules = IRRules()
        item = {
            'ticker': 'META',
            'title': 'Comment on Independent Audit of Community Standards Enforcement Report',
            'content': 'Independent audit and transparency report comment',
            'summary': ''
        }
        result = rules.classify(item)

        assert result['event_hint'] == 'regulatory_policy'
        assert result['pre_score'] == 50
        assert result['need_ai'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
