"""
测试华尔街见闻市场上下文分类
"""
import pytest
from fund_quant.nlp.news_filter.keyword_rules import (
    build_normalized_title,
    classify_wallstreetcn_market_context,
)


class TestNormalizedTitle:
    """测试标题标准化"""

    def test_with_title(self):
        """有标题时使用标题"""
        title = "美国5月零售销售环比增长0.9%"
        content = "财联社6月17日电，美国商务部公布数据显示..."
        result = build_normalized_title(title, content)
        assert result == title

    def test_without_title(self):
        """无标题时从正文提取"""
        title = ""
        content = "财联社6月17日电，美国商务部公布数据显示美国5月零售销售环比增长0.9%。"
        result = build_normalized_title(title, content)
        assert "美国5月零售销售" in result
        assert "财联社6月17日电" not in result


class TestWallstreetcnMarketContext:
    """测试华尔街见闻市场上下文分类"""

    def test_macro_data_low_priority(self):
        """普通宏观数据 - 低优先级"""
        item = {
            'title': '美国5月成屋签约销售指数环比 3.8%，预期 1%',
            'normalized_title': '美国5月成屋签约销售指数环比 3.8%，预期 1%',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'macro_data'
        assert 'US10Y' in result['impact_assets']
        assert 'USD' in result['impact_assets']
        assert result['ai_level'] == 'none'
        assert result['need_ai'] is False

    def test_fed_policy_high_priority(self):
        """美联储决议 - 高优先级"""
        item = {
            'title': '美联储6月决议声明和新闻发布会关注点',
            'normalized_title': '美联储6月决议声明和新闻发布会关注点',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'fed_policy'
        assert 'US10Y' in result['impact_assets']
        assert 'TLT' in result['impact_assets']
        assert result['importance'] == 'high'
        assert result['ai_level'] == 'light'
        assert result['need_ai'] is True

    def test_fed_waller_volatility(self):
        """沃什讲话引发波动"""
        item = {
            'title': '富达称沃什在美联储决议后对通胀的阐释可能引发债市波动',
            'normalized_title': '富达称沃什在美联储决议后对通胀的阐释可能引发债市波动',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'fed_policy'
        assert 'US10Y' in result['impact_assets']
        assert 'TLT' in result['impact_assets']
        assert result['importance'] in ['medium', 'high']
        assert result['ai_level'] == 'light'

    def test_market_move_semiconductor(self):
        """半导体大涨"""
        item = {
            'title': '美股盘初：纳指涨0.5%，费城半导体指数涨近3%，SpaceX涨约4%',
            'normalized_title': '美股盘初：纳指涨0.5%，费城半导体指数涨近3%，SpaceX涨约4%',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] in ['market_move', 'us_equity_sentiment']
        assert 'SMH' in result['impact_assets'] or 'QQQ' in result['impact_assets']
        assert result['market_bias'] == 'risk_on'

    def test_spacex_reversal(self):
        """SpaceX转跌"""
        item = {
            'title': 'SpaceX转跌，此前一度涨超5%',
            'normalized_title': 'SpaceX转跌，此前一度涨超5%',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'market_move'
        assert 'SPACE_THEME' in result['impact_assets'] or 'SATELLITE' in result['impact_assets']
        assert result['market_bias'] == 'risk_off'
        assert result['ai_level'] == 'none'

    def test_commodity_oil_surge(self):
        """原油涨幅达2%"""
        item = {
            'title': '布伦特原油日内涨幅达2.0%',
            'normalized_title': '布伦特原油日内涨幅达2.0%',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'commodity_move'
        assert 'Brent' in result['impact_assets']
        assert 'WTI' in result['impact_assets']
        assert result['importance'] == 'medium'

    def test_geopolitical_hormuz(self):
        """霍尔木兹海峡开放"""
        item = {
            'title': '特朗普重申霍尔木兹海峡将在协议签署之后立即开放',
            'normalized_title': '特朗普重申霍尔木兹海峡将在协议签署之后立即开放',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'geopolitical_energy'
        assert 'WTI' in result['impact_assets']
        assert 'Brent' in result['impact_assets']
        assert result['market_bias'] == 'risk_on'
        assert result['ai_level'] == 'light'

    def test_china_market_policy(self):
        """港股IPO政策"""
        item = {
            'title': '港交所CEO：港股IPO与再融资双热',
            'normalized_title': '港交所CEO：港股IPO与再融资双热',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'china_market_policy'
        assert '港股' in result['impact_assets']
        assert '中国资产' in result['impact_assets']
        assert result['market_bias'] == 'risk_on'

    def test_technology_breakthrough(self):
        """技术突破"""
        item = {
            'title': '我国成功攻克极地船用高强度钢一系列难题',
            'normalized_title': '我国成功攻克极地船用高强度钢一系列难题',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'technology_breakthrough'
        assert '新材料' in result['impact_assets']
        # 无明确A股映射
        assert result['ai_level'] == 'none'
        assert result['need_ai'] is False

    def test_low_value(self):
        """普通讲话 - 低价值"""
        item = {
            'title': '特朗普：美国各项经济数据都非常出色',
            'normalized_title': '特朗普：美国各项经济数据都非常出色',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'low_value'
        assert result['ai_level'] == 'none'
        assert result['need_ai'] is False

    def test_waller_bond_volatility(self):
        """沃什立场加剧美债波动"""
        item = {
            'title': '高盛认为沃什的立场将加剧短端美债波动性',
            'normalized_title': '高盛认为沃什的立场将加剧短端美债波动性',
            'content': '高盛认为沃什的立场将加剧短端美债波动性，使长端曲线更趋平稳',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'fed_policy'
        assert 'US2Y' in result['impact_assets']
        assert 'US10Y' in result['impact_assets']
        assert 'TLT' in result['impact_assets']
        assert result['market_bias'] == 'risk_off'
        assert result['importance'] == 'high'
        assert result['ai_level'] == 'light'
        assert result['need_ai'] is True

    def test_geopolitical_weak(self):
        """普通地缘谴责 - 弱市场影响"""
        item = {
            'title': '多国强烈谴责以色列定居者袭击约旦河西岸清真寺',
            'normalized_title': '多国强烈谴责以色列定居者袭击约旦河西岸清真寺',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'geopolitical'
        assert result['importance'] == 'low'
        assert result['ai_level'] == 'none'
        assert result['need_ai'] is False

    def test_hormuz_demining(self):
        """霍尔木兹扫雷 - 地缘能源"""
        item = {
            'title': '德国总理默茨：德国可以帮助在霍尔木兹海峡扫雷',
            'normalized_title': '德国总理默茨：德国可以帮助在霍尔木兹海峡扫雷',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'geopolitical_energy'
        assert 'WTI' in result['impact_assets']
        assert 'Brent' in result['impact_assets']
        assert result['importance'] in ['medium', 'high']
        assert result['ai_level'] == 'light'

    def test_amazon_ai_chip(self):
        """亚马逊AI芯片竞品"""
        item = {
            'title': '报道：亚马逊洽谈向其他公司出售英伟达竞品芯片',
            'normalized_title': '报道：亚马逊洽谈向其他公司出售英伟达竞品芯片',
            'content': '',
        }
        result = classify_wallstreetcn_market_context(item)

        assert result['context_type'] == 'us_equity_sentiment'
        assert 'AMZN' in result['impact_assets']
        assert 'NVDA' in result['impact_assets']
        assert 'SMH' in result['impact_assets']
        assert 'ai_compute' in result['theme_hint_ids'] or 'ai_chip' in result['theme_hint_ids']
        assert result['market_bias'] == 'mixed'
        assert result['ai_level'] == 'light'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
