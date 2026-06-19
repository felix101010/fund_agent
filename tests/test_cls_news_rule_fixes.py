"""
测试 CLS 新闻规则修复
"""
import pytest

from fund_quant.data_sources.news.cls_api_collector import build_normalized_title
from fund_quant.nlp.news_filter.keyword_rules import (
    extract_stocks_by_code_pattern,
    classify_overseas_ai_infrastructure,
    classify_apple_ai_terminal,
    fix_war_drone_theme,
    apply_ai_level,
)
from fund_quant.nlp.news_filter.paid_content_detector import (
    is_paid_research_teaser,
    classify_paid_research_teaser,
)


class TestNormalizedTitle:
    """测试 normalized_title 生成"""

    def test_empty_title_with_cls_prefix(self):
        """title 为空，content 有财联社前缀"""
        title = ""
        content = "财联社6月15日电，谷歌宣布将投资15亿美元，用于在2026年和2027年扩建位于阿拉巴马州杰克逊县的数据中心园区。"

        normalized = build_normalized_title(title, content)

        assert normalized
        assert "财联社6月15日电" not in normalized
        assert "谷歌" in normalized

    def test_non_empty_title(self):
        """title 非空"""
        title = "【电报解读】HVLP算力铜箔成关键基材"
        content = "正文内容"

        normalized = build_normalized_title(title, content)

        assert normalized
        assert "电报解读" in normalized or "HVLP" in normalized

    def test_title_with_brackets(self):
        """title 包含【】标签"""
        title = "【公告全知道】MLCC+光通信+芯片"
        content = ""

        normalized = build_normalized_title(title, content)

        assert normalized
        # 【】标签可能被移除
        assert "MLCC" in normalized or "公告全知道" in normalized


class TestStockCodeExtractor:
    """测试股票代码硬解析"""

    def test_extract_sh_stock(self):
        """提取上交所股票"""
        text = "复星医药(600196.SH)公告称"

        stocks = extract_stocks_by_code_pattern(text)

        assert len(stocks) == 1
        assert stocks[0]['code'] == '600196.SH'
        assert stocks[0]['name'] == '复星医药'
        assert stocks[0]['match_type'] == 'name_code_pattern'
        assert stocks[0]['confidence'] == 1.0

    def test_extract_sz_stock(self):
        """提取深交所股票"""
        text = "粤万年青(301111.SZ)发布公告"

        stocks = extract_stocks_by_code_pattern(text)

        assert len(stocks) == 1
        assert stocks[0]['code'] == '301111.SZ'
        assert stocks[0]['name'] == '粤万年青'

    def test_extract_stock_without_suffix(self):
        """提取没有后缀的股票代码，自动补全"""
        text = "复星医药（600196）公告"

        stocks = extract_stocks_by_code_pattern(text)

        assert len(stocks) == 1
        assert stocks[0]['code'] == '600196.SH'  # 自动补全
        assert stocks[0]['name'] == '复星医药'

    def test_extract_multiple_stocks(self):
        """提取多个股票"""
        text = "复星医药(600196.SH)和爱迪特(301580.SZ)公告"

        stocks = extract_stocks_by_code_pattern(text)

        assert len(stocks) == 2
        codes = [s['code'] for s in stocks]
        assert '600196.SH' in codes
        assert '301580.SZ' in codes

    def test_no_stock_in_text(self):
        """文本中没有股票代码"""
        text = "谷歌宣布投资数据中心"

        stocks = extract_stocks_by_code_pattern(text)

        assert len(stocks) == 0


class TestPaidResearchTeaser:
    """测试付费研报标题"""

    def test_is_paid_research_teaser(self):
        """识别付费研报标题"""
        title = "【电报解读】HVLP算力铜箔成关键基材"

        assert is_paid_research_teaser(title) is True

    def test_classify_paid_teaser(self):
        """分类付费研报"""
        item = {
            'title': '【电报解读】HVLP算力铜箔成关键基材，业内称在手订单已排至2027年下半年',
            'content': '',
            'related_stocks': []
        }

        result = classify_paid_research_teaser(item)

        assert result['event_type'] == 'paid_research_teaser'
        assert result['ai_level'] == 'light'
        assert result['can_trade_directly'] is False
        assert result['need_manual_followup'] is True
        assert 'teaser_no_full_content' in result['risk_flags']
        assert result['confidence'] == 0.55

    def test_paid_teaser_theme_extraction(self):
        """付费研报主题提取"""
        item = {
            'title': '【风口研报】前瞻布局高速背板、液冷互连及光模块',
            'content': '',
        }

        result = classify_paid_research_teaser(item)

        assert 'theme_ids' in result
        # 应该包含相关主题
        assert any(theme in result['theme_ids'] for theme in ['ai_compute', 'optical_module', 'liquid_cooling'])


class TestOverseasAIInfrastructure:
    """测试海外 AI 基建主题"""

    def test_google_datacenter_investment(self):
        """谷歌数据中心投资"""
        item = {
            'title': '',
            'normalized_title': '谷歌宣布将投资15亿美元用于扩建阿拉巴马州数据中心园区',
            'content': '谷歌宣布将投资15亿美元，用于在2026年和2027年扩建位于阿拉巴马州杰克逊县的数据中心园区。',
        }

        result = classify_overseas_ai_infrastructure(item)

        assert result is not None
        assert result['primary_theme_id'] == 'ai_compute'
        assert result['primary_theme_name'] == 'AI算力'
        assert result['event_type'] == 'ai_infrastructure_investment'
        assert result['final_score'] == 65
        assert result['trade_priority'] == 'candidate'

    def test_equinix_cisco_nvidia_cooperation(self):
        """Equinix 携手思科与英伟达部署AI工厂"""
        item = {
            'title': 'Equinix携手思科与英伟达部署AI工厂',
            'normalized_title': 'Equinix携手思科与英伟达部署AI工厂',
            'content': '',
        }

        result = classify_overseas_ai_infrastructure(item)

        assert result is not None
        assert result['primary_theme_id'] == 'ai_compute'
        assert result['event_type'] == 'strategic_cooperation'

    def test_nvidia_financing(self):
        """英伟达发债筹资"""
        item = {
            'title': '英伟达计划通过发行高等级债券筹资至少200亿美元用于AI基础设施',
            'normalized_title': '英伟达计划通过发行高等级债券筹资至少200亿美元用于AI基础设施',
            'content': '英伟达计划通过发行债券筹资用于扩建AI基础设施和数据中心',
        }

        result = classify_overseas_ai_infrastructure(item)

        assert result is not None
        assert result['primary_theme_id'] == 'ai_compute'
        assert result['event_type'] == 'financing_for_ai_capex'
        assert result['final_score'] == 50  # 发债不打高分
        assert result['trade_priority'] == 'watch'


class TestWarDroneFix:
    """测试战争无人机修正"""

    def test_war_drone_refinery_attack(self):
        """俄罗斯炼油厂遭无人机袭击"""
        item = {
            'title': '',
            'normalized_title': '俄罗斯TANECO炼油厂遭无人机袭击后暂停运营',
            'content': '财联社6月15日电，消息人士称，俄罗斯TANECO炼油厂在6月12日遭无人机袭击后暂停运营。',
            'primary_theme_id': 'low_altitude_economy',
            'risk_flags': []
        }

        result = fix_war_drone_theme(item)

        assert result['primary_theme_id'] != 'low_altitude_economy'
        assert result['event_type'] == 'geopolitical_risk'
        assert 'war_drone_not_low_altitude' in result['risk_flags']
        assert result['ai_level'] == 'none'

    def test_war_drone_with_energy(self):
        """战争无人机 + 能源关键词"""
        item = {
            'title': '',
            'normalized_title': '乌克兰无人机袭击俄罗斯炼油厂',
            'content': '乌克兰无人机袭击俄罗斯炼油厂，原油供应受影响',
            'primary_theme_id': 'low_altitude_economy',
            'risk_flags': []
        }

        result = fix_war_drone_theme(item)

        assert result['primary_theme_id'] == 'energy_risk'
        assert result['primary_theme_name'] == '能源风险'

    def test_normal_low_altitude_drone(self):
        """国内低空物流无人机，不应修正"""
        item = {
            'title': '国内低空物流无人机商业化运营加速',
            'normalized_title': '国内低空物流无人机商业化运营加速',
            'content': '顺丰无人机配送网络覆盖全国',
            'primary_theme_id': 'low_altitude_economy',
            'risk_flags': []
        }

        result = fix_war_drone_theme(item)

        # 不包含战争关键词，不应修正
        assert result['primary_theme_id'] == 'low_altitude_economy'


class TestAILevel:
    """测试 ai_level 分级"""

    def test_paid_teaser_light(self):
        """付费研报 → light"""
        item = {
            'event_type': 'paid_research_teaser',
            'final_score': 55,
            'related_stocks_count': 0,
        }

        result = apply_ai_level(item)

        assert result['ai_level'] == 'light'
        assert result['need_ai'] is True

    def test_strong_catalyst_deep(self):
        """强催化剂 → deep"""
        item = {
            'event_type': 'order_win',
            'final_score': 70,
            'related_stocks_count': 1,
        }

        result = apply_ai_level(item)

        assert result['ai_level'] == 'deep'
        assert result['need_ai'] is True

    def test_war_drone_none(self):
        """战争无人机 → none"""
        item = {
            'event_type': 'geopolitical_risk',
            'final_score': 40,
            'risk_flags': ['war_drone_not_low_altitude'],
        }

        result = apply_ai_level(item)

        assert result['ai_level'] == 'none'
        assert result['need_ai'] is False

    def test_general_low_score_none(self):
        """general + 低分 + 无题材 → none"""
        item = {
            'event_type': 'general',
            'final_score': 40,
            'related_stocks_count': 0,
            'primary_theme_id': None,
        }

        result = apply_ai_level(item)

        assert result['ai_level'] == 'none'
        assert result['need_ai'] is False

    def test_high_score_with_stock_deep(self):
        """高分 + 有股票 → deep"""
        item = {
            'event_type': 'capacity_build',
            'final_score': 65,
            'related_stocks_count': 1,
        }

        result = apply_ai_level(item)

        assert result['ai_level'] == 'deep'
        assert result['need_ai'] is True


class TestEnhancedRules:
    """测试增强规则（第二批）"""

    def test_paid_teaser_extended(self):
        """付费研报扩展识别"""
        item = {
            'title': '【研选•研报数据】AI持续拉动光芯片需求，关键材料体系磷化铟或迎共振式增长窗口期；公司晋身Low-Dk二代布龙头，Low CTE布快速突破，充分受益AI超级周期爆发',
            'content': '',
            'related_stocks': []
        }

        # 应该识别为付费研报
        assert is_paid_research_teaser(item['title']) is True

        result = classify_paid_research_teaser(item)

        assert result['event_type'] == 'paid_research_teaser'
        assert 'ai_compute' in result.get('theme_ids', [])
        assert 'optical_module' in result.get('theme_ids', [])
        assert 'semiconductor_material' in result.get('theme_ids', [])
        assert result['can_trade_directly'] is False
        assert result['need_manual_followup'] is True
        assert 'teaser_no_full_content' in result['risk_flags']

    def test_war_drone_bus_attack(self):
        """战争无人机袭击客车"""
        item = {
            'title': '俄侦委以恐袭立案调查白俄罗斯少年球队客车遇袭事件',
            'normalized_title': '俄侦委以恐袭立案调查白俄罗斯少年球队客车遇袭事件',
            'content': '乌军使用攻击型无人机袭击俄罗斯公路客车',
            'primary_theme_id': 'low_altitude_economy',
            'risk_flags': []
        }

        result = fix_war_drone_theme(item)

        assert result['primary_theme_id'] != 'low_altitude_economy'
        assert result['event_type'] == 'geopolitical_risk'
        assert result['need_ai'] is False
        assert result['ai_level'] == 'none'
        assert 'war_drone_not_low_altitude' in result['risk_flags']

    def test_hpe_nvidia_enterprise_ai(self):
        """慧与科技+英伟达企业AI合作"""
        item = {
            'title': '慧与科技表示，携手英伟达将代理式人工智能引入生产环境',
            'normalized_title': '慧与科技表示，携手英伟达将代理式人工智能引入生产环境',
            'content': '',
        }

        result = classify_overseas_ai_infrastructure(item)

        assert result is not None
        assert result['primary_theme_id'] == 'ai_compute'
        assert result['event_type'] == 'enterprise_ai_cooperation'
        assert result['ai_level'] == 'light'
        assert result['final_score'] == 55

    def test_microsoft_copilot_deepseek(self):
        """微软Copilot+DeepSeek"""
        item = {
            'title': '微软据称考虑将DeepSeek用于Copilot协同工作平台',
            'normalized_title': '微软据称考虑将DeepSeek用于Copilot协同工作平台',
            'content': '',
        }

        result = classify_overseas_ai_infrastructure(item)

        assert result is not None
        assert result['primary_theme_id'] == 'ai_software'
        assert result['primary_theme_name'] == 'AI软件'
        assert result['event_type'] == 'ai_product_update'
        assert result['ai_level'] == 'light'

    def test_microsoft_copilot_release(self):
        """微软Copilot功能推出"""
        item = {
            'title': '',
            'normalized_title': '微软表示Copilot协作功能现已全面推出',
            'content': '财联社6月17日电，微软表示，Copilot协作功能现已全面推出。',
        }

        result = classify_overseas_ai_infrastructure(item)

        assert result is not None
        assert result['primary_theme_id'] == 'ai_software'
        assert result['event_type'] == 'ai_product_update'

    def test_apple_airpods_foldable_iphone(self):
        """苹果AirPods+折叠iPhone"""
        item = {
            'title': '苹果计划2027年将推出带摄像头AirPods与新一代折叠iPhone',
            'normalized_title': '苹果计划2027年将推出带摄像头AirPods与新一代折叠iPhone',
            'content': '',
        }

        result = classify_apple_ai_terminal(item)

        assert result is not None
        assert result['primary_theme_id'] == 'consumer_electronics'
        assert result['primary_theme_name'] == '消费电子'
        assert result['event_type'] == 'ai_terminal_product'
        assert 'ai_terminal' in result['theme_ids']
        assert 'ai_wearable' in result['theme_ids']
        assert 'foldable_phone' in result['theme_ids']
        # 不应该是半导体材料
        assert result['primary_theme_id'] != 'semiconductor_material'

    def test_general_low_score_archive(self):
        """general低分无主题archive"""
        item = {
            'title': '高盛2026年并购业务突破1万亿美元',
            'normalized_title': '高盛2026年并购业务突破1万亿美元',
            'content': '',
            'event_type': 'general',
            'final_score': 10,
            'primary_theme_id': None,
            'related_stocks_count': 0,
        }

        result = apply_ai_level(item)

        assert result['ai_level'] == 'none'
        assert result['need_ai'] is False
        assert result['trade_priority'] == 'archive'

    def test_general_low_score_with_ai_keywords(self):
        """general低分但有AI关键词，给light"""
        item = {
            'title': '微软据悉曾就租赁甲骨文云资源事宜进行谈判',
            'normalized_title': '微软据悉曾就租赁甲骨文云资源事宜进行谈判',
            'content': '',
            'event_type': 'general',
            'final_score': 30,
            'primary_theme_id': None,
            'related_stocks_count': 0,
        }

        result = apply_ai_level(item)

        # 有微软关键词，应该给light
        assert result['ai_level'] == 'light'
        assert result['need_ai'] is True
        assert result['final_score'] >= 45

    def test_normalized_title_print(self):
        """normalized_title生成和打印"""
        title = ""
        content = "财联社6月17日电，微软表示，Copilot协作功能现已全面推出。"

        normalized = build_normalized_title(title, content)

        assert normalized
        assert "财联社6月17日电" not in normalized
        assert "微软" in normalized
        assert "Copilot" in normalized


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
