"""
测试 AIOutputPostProcessor（增强版）
"""
import pytest
from datetime import datetime
from fund_quant.nlp.news_filter import NewsItem, FilterResult
from fund_quant.nlp.news_ai.ai_event_models import AIEventResult, RelatedStock
from fund_quant.nlp.news_ai.ai_output_post_processor_enhanced import AIOutputPostProcessor


def test_capacity_build_correction():
    """江丰电子建设先进制程靶材生产基地 → event_type=capacity_build, theme=半导体材料（不是江丰电子）"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_001",
        source="cls",
        title="江丰电子：公司正在韩国建设先进制程靶材生产基地",
        content="江丰电子在韩国建设靶材生产基地",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_001",
        action="unknown",
        need_ai=True,
        pre_score=60,
        matched_keywords=["公司", "建设", "生产基地"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_001",
        is_market_relevant=True,
        event_type="general",
        theme="江丰电子",  # AI错误输出为公司名
        sub_themes=[],
        related_stocks=[RelatedStock(name="江丰电子", code="", reason="主体公司")],
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.6
    )

    result = processor.process(news, filter_result, ai_result)

    assert result.event_type == "capacity_build"
    assert result.theme == "半导体材料"  # 应该转换为产业主题
    assert result.event_level == "B"
    assert len(result.related_stocks) == 1
    assert result.related_stocks[0].code == "300666.SZ"
    assert any("theme company_name" in note for note in result.postprocess_notes)


def test_supply_chain_correction():
    """江丰电子高纯300mm硅靶批量供货 → event_type=supply_chain, event_level=A, sentiment=positive"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_002",
        source="cls",
        title="江丰电子高纯300mm硅靶批量供货",
        content="江丰电子的硅靶材料批量供货给客户",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_002",
        action="candidate",
        need_ai=True,
        pre_score=70,
        matched_keywords=["批量供货"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_002",
        is_market_relevant=True,
        event_type="general",
        theme="半导体",
        sub_themes=[],
        related_stocks=[RelatedStock(name="江丰电子", code="300666.SZ", reason="供货主体")],
        sentiment="neutral",
        event_level="B",
        novelty_type="old_theme_repeat",
        summary="",
        confidence=0.7
    )

    result = processor.process(news, filter_result, ai_result)

    assert result.event_type == "supply_chain"
    assert result.event_level == "A"
    assert result.sentiment == "positive"
    assert result.novelty_type == "old_theme_new_progress"


def test_product_release_with_robot():
    """智平方发布类脑式具身智能系统NeuroVLA → event_type=product_release, theme=机器人"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_003",
        source="cls",
        title="智平方发布类脑式具身智能系统NeuroVLA",
        content="智平方公司发布具身智能机器人系统",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_003",
        action="candidate",
        need_ai=True,
        pre_score=65,
        matched_keywords=["发布"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_003",
        is_market_relevant=True,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[],
        sentiment="neutral",
        event_level="C",
        novelty_type="new_theme",
        summary="",
        confidence=0.6
    )

    result = processor.process(news, filter_result, ai_result)

    assert result.event_type == "product_release"
    assert result.theme == "机器人"
    assert result.event_level == "B"
    assert result.novelty_type == "new_theme"  # 允许保留，因为有"发布"


def test_geopolitical_noise():
    """伊朗司法总监：绝不信任美国 → is_market_relevant=False, novelty_type=noise, no stocks"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_004",
        source="cls",
        title="伊朗司法总监：绝不信任美国",
        content="伊朗司法总监表示绝不信任美国",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_004",
        action="unknown",
        need_ai=False,
        pre_score=20,
        matched_keywords=[],
        matched_rules=[],
        reasons=["地缘政治"],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_004",
        is_market_relevant=True,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="伊朗司法总监", code="", reason="人物"),
            RelatedStock(name="美国", code="", reason="国家")
        ],
        sentiment="neutral",
        event_level="C",
        novelty_type="new_theme",
        summary="",
        confidence=0.5
    )

    result = processor.process(news, filter_result, ai_result)

    assert result.is_market_relevant is False
    assert result.novelty_type == "noise"
    assert len(result.related_stocks) == 0
    assert len(result.related_entities) == 2
    assert result.confidence <= 0.4


def test_association_entity():
    """中国摩托车商会倡议 → related_stocks 为空，商会移到 entities"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_005",
        source="cls",
        title="中国摩托车商会发布行业倡议",
        content="中国摩托车商会发布倡议",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_005",
        action="unknown",
        need_ai=False,
        pre_score=25,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_005",
        is_market_relevant=True,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="中国摩托车商会", code="", reason="发布主体")
        ],
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.5
    )

    result = processor.process(news, filter_result, ai_result)

    assert len(result.related_stocks) == 0
    assert len(result.related_entities) == 1
    assert result.related_entities[0].name == "中国摩托车商会"


def test_new_theme_downgrade_for_diplomatic():
    """外交表态新闻 → novelty_type 不允许为 new_theme"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_006",
        source="cls",
        title="某国外交部发表讲话",
        content="外交部讲话表态期待未来合作",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_006",
        action="unknown",
        need_ai=False,
        pre_score=20,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_006",
        is_market_relevant=True,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[],
        sentiment="neutral",
        event_level="C",
        novelty_type="new_theme",
        summary="",
        confidence=0.6
    )

    result = processor.process(news, filter_result, ai_result)

    assert result.novelty_type == "noise"  # 应该被降级
    assert any("novelty_type降级" in note for note in result.postprocess_notes)


def test_regulatory_investigation():
    """审查调查新闻 → event_type=regulatory_investigation, sentiment=negative, novelty=negative_disconfirm"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_007",
        source="cls",
        title="某公司高管接受审查调查",
        content="某上市公司高管涉嫌违纪违法接受纪律审查和监察调查",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_007",
        action="risk",
        need_ai=True,
        pre_score=90,
        matched_keywords=["审查调查"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_007",
        is_market_relevant=True,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[],
        sentiment="neutral",
        event_level="B",
        novelty_type="noise",
        summary="",
        confidence=0.7
    )

    result = processor.process(news, filter_result, ai_result)

    assert result.event_type == "regulatory_investigation"
    assert result.sentiment == "negative"
    assert result.novelty_type == "negative_disconfirm"
    assert result.event_level == "B"  # 保持原等级


def test_price_increase():
    """涨价新闻 → event_type=price_increase, event_level=A, sentiment=positive"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_008",
        source="cls",
        title="某公司产品涨价",
        content="公司宣布产品提价10%",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_008",
        action="candidate",
        need_ai=True,
        pre_score=75,
        matched_keywords=["涨价"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_008",
        is_market_relevant=True,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[],
        sentiment="neutral",
        event_level="B",
        novelty_type="noise",
        summary="",
        confidence=0.6
    )

    result = processor.process(news, filter_result, ai_result)

    assert result.event_type == "price_increase"
    assert result.event_level == "A"
    assert result.sentiment == "positive"
