"""
AI 事件抽取器测试
"""
import json
import pytest
from datetime import datetime

from fund_quant.nlp.news_filter.filter_models import NewsItem, FilterResult
from fund_quant.nlp.news_ai import AIEventExtractor


@pytest.fixture
def extractor():
    """创建抽取器实例（不带 LLM 客户端，使用 fallback）"""
    return AIEventExtractor(llm_client=None)


def test_should_not_extract_when_need_ai_false(extractor):
    """测试：need_ai=False 时，不调用 AI，返回空事件，is_valid=True"""
    news = NewsItem(
        news_id="test_001",
        source="cls",
        title="低价值新闻",
        content="专家表示市场长期向好。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_001",
        action="low_value",
        need_ai=False,
        pre_score=25
    )

    result = extractor.extract(news, filter_result)

    assert result.is_market_relevant is False
    assert result.event_type == "general"
    assert result.theme == ""
    assert result.sentiment == "neutral"
    assert result.event_level == "C"
    assert result.novelty_type == "noise"
    assert result.confidence == 0.0
    assert result.is_valid is True
    assert len(result.validation_errors) == 0


def test_risk_news_fallback(extractor):
    """测试：risk 新闻 fallback 输出"""
    news = NewsItem(
        news_id="test_002",
        source="cls",
        title="公司澄清：暂无相关业务",
        content="公司澄清，暂无相关业务。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_002",
        action="risk",
        need_ai=True,
        pre_score=90,
        risk_flags=["澄清", "暂无相关业务"]
    )

    result = extractor.extract(news, filter_result)

    assert result.event_type == "risk_disconfirm"
    assert result.sentiment == "negative"
    assert result.novelty_type == "negative_disconfirm"
    assert result.event_level == "A"
    assert result.confidence == 0.80
    assert result.is_valid is True


def test_verification_pass_event(extractor):
    """测试：'验证通过' 新闻输出 event_type='verification_pass'，event_level='A'"""
    news = NewsItem(
        news_id="test_003",
        source="cls",
        title="某公司产品验证通过",
        content="公司新产品已验证通过客户测试。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_003",
        action="analyze",
        need_ai=True,
        pre_score=85
    )

    result = extractor.extract(news, filter_result)

    assert result.event_type == "verification_pass"
    assert result.event_level == "A"
    assert result.sentiment == "positive"
    assert result.confidence >= 0.80


def test_sample_delivery_event(extractor):
    """测试：'送样' 新闻输出 event_type='sample_delivery'，event_level='A'"""
    news = NewsItem(
        news_id="test_004",
        source="cls",
        title="公司向英伟达送样M10材料",
        content="公司已向英伟达送样M10覆铜板材料。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_004",
        action="analyze",
        need_ai=True,
        pre_score=85
    )

    result = extractor.extract(news, filter_result)

    assert result.event_type == "sample_delivery"
    assert result.event_level == "A"
    assert result.sentiment == "positive"


def test_mass_production_event(extractor):
    """测试：'量产' 新闻输出 event_type='mass_production'"""
    news = NewsItem(
        news_id="test_005",
        source="cls",
        title="公司新产品实现量产",
        content="公司宣布新产品已实现量产。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_005",
        action="analyze",
        need_ai=True,
        pre_score=85
    )

    result = extractor.extract(news, filter_result)

    assert result.event_type == "mass_production"
    assert result.sentiment == "positive"
    assert result.event_level == "A"


def test_order_win_event(extractor):
    """测试：'中标' 新闻输出 event_type='order_win'"""
    news = NewsItem(
        news_id="test_006",
        source="cls",
        title="公司成功中标大单",
        content="公司成功中标某重大项目订单。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_006",
        action="analyze",
        need_ai=True,
        pre_score=85
    )

    result = extractor.extract(news, filter_result)

    assert result.event_type == "order_win"
    assert result.sentiment == "positive"


def test_theme_nvidia_m10(extractor):
    """测试：包含'英伟达'或'M10'时 theme='英伟达M10材料'"""
    news = NewsItem(
        news_id="test_007",
        source="cls",
        title="英伟达M10材料进展",
        content="公司M10覆铜板送样英伟达。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_007",
        action="analyze",
        need_ai=True,
        pre_score=85
    )

    result = extractor.extract(news, filter_result)

    assert result.theme == "英伟达M10材料"


def test_theme_robot(extractor):
    """测试：包含'机器人'时 theme='机器人'"""
    news = NewsItem(
        news_id="test_008",
        source="cls",
        title="人形机器人技术突破",
        content="公司在人形机器人领域取得重大突破。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_008",
        action="candidate",
        need_ai=True,
        pre_score=65
    )

    result = extractor.extract(news, filter_result)

    assert result.theme == "机器人"


def test_theme_optical_module(extractor):
    """测试：包含'光模块'或'CPO'时 theme='光模块/CPO'"""
    news = NewsItem(
        news_id="test_009",
        source="cls",
        title="光模块行业新进展",
        content="公司CPO技术获得突破。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_009",
        action="candidate",
        need_ai=True,
        pre_score=65
    )

    result = extractor.extract(news, filter_result)

    assert result.theme == "光模块/CPO"


def test_related_stocks_identification(extractor):
    """测试：包含'生益科技'时 related_stocks 包含 code='600183.SH'"""
    news = NewsItem(
        news_id="test_010",
        source="cls",
        title="生益科技M10材料送样进展",
        content="生益科技M10覆铜板已送样英伟达。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_010",
        action="analyze",
        need_ai=True,
        pre_score=85
    )

    result = extractor.extract(news, filter_result)

    assert len(result.related_stocks) > 0
    stock_codes = [s.code for s in result.related_stocks]
    assert "600183.SH" in stock_codes

    # 检查股票信息完整性
    for stock in result.related_stocks:
        if stock.code == "600183.SH":
            assert stock.name == "生益科技"
            assert stock.reason == "新闻中提及该公司"


def test_with_mock_llm_client(extractor):
    """测试：传入 mock llm_client，generate 返回合法 JSON，extract 能解析成功"""

    # Mock LLM 客户端
    class MockLLMClient:
        def generate(self, prompt: str) -> str:
            return json.dumps({
                "is_market_relevant": True,
                "event_type": "sample_delivery",
                "theme": "英伟达M10材料",
                "sub_themes": ["高速PCB", "覆铜板"],
                "related_stocks": [
                    {
                        "code": "600183.SH",
                        "name": "生益科技",
                        "reason": "M10覆铜板送样"
                    }
                ],
                "sentiment": "positive",
                "event_level": "A",
                "novelty_type": "old_theme_new_progress",
                "summary": "生益科技M10覆铜板送样英伟达",
                "confidence": 0.86,
                "risk_flags": []
            }, ensure_ascii=False)

    extractor_with_llm = AIEventExtractor(llm_client=MockLLMClient())

    news = NewsItem(
        news_id="test_011",
        source="cls",
        title="生益科技M10材料送样",
        content="生益科技M10覆铜板已送样英伟达。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_011",
        action="analyze",
        need_ai=True,
        pre_score=85
    )

    result = extractor_with_llm.extract(news, filter_result)

    assert result.is_valid is True
    assert result.event_type == "sample_delivery"
    assert result.theme == "英伟达M10材料"
    assert result.sentiment == "positive"
    assert result.event_level == "A"
    assert result.confidence == 0.86
    assert len(result.related_stocks) == 1
    assert result.related_stocks[0].code == "600183.SH"


def test_ai_invalid_fallback_for_risk_news():
    """测试：mock llm 返回 positive，但当前新闻是 risk，应自动 fallback"""

    class MockLLMClient:
        def generate(self, prompt: str) -> str:
            # AI 错误输出：照抄了示例，输出 positive
            return json.dumps({
                "is_market_relevant": True,
                "event_type": "sample_delivery",
                "theme": "英伟达M10材料",
                "sub_themes": ["高速PCB"],
                "related_stocks": [
                    {"code": "600183.SH", "name": "生益科技", "reason": "送样"}
                ],
                "sentiment": "positive",  # 错误：risk 新闻不应该是 positive
                "event_level": "A",
                "novelty_type": "old_theme_new_progress",
                "summary": "测试",
                "confidence": 0.86,
                "risk_flags": []
            }, ensure_ascii=False)

    extractor = AIEventExtractor(llm_client=MockLLMClient())

    news = NewsItem(
        news_id="test_risk_001",
        source="cls",
        title="某公司澄清：暂无相关人形机器人业务",
        content="某公司今日发布澄清公告，称公司目前暂无相关人形机器人业务。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_risk_001",
        action="risk",
        need_ai=True,
        pre_score=90,
        risk_flags=["澄清", "暂无相关业务"]
    )

    result = extractor.extract(news, filter_result)

    # 应自动 fallback
    assert result.is_valid is True
    assert result.event_type == "risk_disconfirm"
    assert result.sentiment == "negative"
    assert result.novelty_type == "negative_disconfirm"
    assert any("fallback" in err.lower() for err in result.validation_errors)


def test_fallback_for_zhongxing_optical_module():
    """测试：fallback 对'中兴通讯800G光模块量产'的识别"""
    extractor = AIEventExtractor(llm_client=None)

    news = NewsItem(
        news_id="test_zx_001",
        source="cls",
        title="中兴通讯：800G光模块已实现量产",
        content="中兴通讯宣布，公司800G光模块产品已实现量产，并已向多个客户批量供货。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_zx_001",
        action="analyze",
        need_ai=True,
        pre_score=85
    )

    result = extractor.extract(news, filter_result)

    assert result.event_type == "mass_production"
    assert result.theme == "光模块/CPO"
    assert result.sentiment == "positive"
    assert result.event_level == "A"

    # 检查关联股票
    stock_codes = [s.code for s in result.related_stocks]
    stock_names = [s.name for s in result.related_stocks]
    assert "000063.SZ" in stock_codes
    assert "中兴通讯" in stock_names


def test_fallback_for_robot_risk_news():
    """测试：fallback 对'某公司澄清暂无人形机器人业务'的识别"""
    extractor = AIEventExtractor(llm_client=None)

    news = NewsItem(
        news_id="test_robot_risk",
        source="cls",
        title="某公司澄清：暂无相关人形机器人业务",
        content="某公司今日发布澄清公告，称公司目前暂无相关人形机器人业务。",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_robot_risk",
        action="risk",
        need_ai=True,
        pre_score=90,
        risk_flags=["澄清", "暂无相关业务"]
    )

    result = extractor.extract(news, filter_result)

    assert result.event_type == "risk_disconfirm"
    assert result.theme == "机器人"
    assert result.sentiment == "negative"
    assert result.novelty_type == "negative_disconfirm"
    assert result.event_level == "A"
