"""
测试包钢股份AI炼钢案例
"""
import pytest
from datetime import datetime
from fund_quant.nlp.news_filter import NewsItem, FilterResult
from fund_quant.nlp.news_ai.ai_event_models import AIEventResult, RelatedStock
from fund_quant.nlp.news_ai.ai_output_post_processor_enhanced import AIOutputPostProcessor


def test_baogang_ai_steel():
    """包钢股份AI炼钢项目 → theme=AI工业应用, stock=包钢股份 600010.SH"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_baogang",
        source="cls",
        title="包钢股份AI炼钢项目正式投用",
        content="包钢股份的AI炼钢项目正式投用，实现智能制造",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_baogang",
        action="candidate",
        need_ai=True,
        pre_score=65,
        matched_keywords=["投用", "AI"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_baogang",
        is_market_relevant=True,
        event_type="general",
        theme="包钢股份",  # AI输出为公司名
        sub_themes=[],
        related_stocks=[],  # AI可能没识别出
        sentiment="positive",
        event_level="B",
        novelty_type="old_theme_new_progress",
        summary="",
        confidence=0.7
    )

    result = processor.process(news, filter_result, ai_result)

    # theme应该转换为AI工业应用
    assert "AI工业应用" in result.theme or "AI" in result.theme.lower()

    # 应该从文本中补充包钢股份
    assert len(result.related_stocks) >= 1
    stock_codes = [s.code for s in result.related_stocks]
    assert "600010.SH" in stock_codes


def test_jd_health_ai_medical():
    """京东健康专科大模型 → stock=京东健康 06618.HK, theme=AI医疗"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_jdh",
        source="cls",
        title="京东健康与北京友谊医院达成合作 将共同建设消化系统专科大模型",
        content="京东健康与北京友谊医院达成战略合作，建设AI大模型",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_jdh",
        action="candidate",
        need_ai=True,
        pre_score=70,
        matched_keywords=["大模型", "合作"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_jdh",
        is_market_relevant=True,
        event_type="strategic_cooperation",
        theme="京东健康",  # AI输出为公司名
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="京东健康", code="", reason="合作主体"),
            RelatedStock(name="北京友谊医院", code="", reason="合作方")
        ],
        sentiment="positive",
        event_level="B",
        novelty_type="new_theme",
        summary="",
        confidence=0.85
    )

    result = processor.process(news, filter_result, ai_result)

    # theme应该转换为AI医疗
    assert result.theme == "AI医疗"

    # 应该有京东健康股票
    assert len(result.related_stocks) >= 1
    stock_names = [s.name for s in result.related_stocks]
    stock_codes = [s.code for s in result.related_stocks]
    assert "京东健康" in stock_names
    assert "06618.HK" in stock_codes

    # 北京友谊医院应该在entities中
    assert len(result.related_entities) >= 1
    entity_names = [e.name for e in result.related_entities]
    assert "北京友谊医院" in entity_names
