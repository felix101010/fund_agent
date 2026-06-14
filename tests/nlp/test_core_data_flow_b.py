"""
测试核心数据流（B批实施）
验证：AIEventResult扩展 → Validator强化 → PostProcessor增强 → ThemeNormalizer → MarketEnricher → EventScorer
"""
import pytest
from datetime import datetime
from fund_quant.nlp.news_filter import NewsItem, FilterResult
from fund_quant.nlp.news_ai.ai_event_models import AIEventResult, RelatedStock
from fund_quant.nlp.news_ai.ai_output_post_processor_enhanced import AIOutputPostProcessor


def test_core_data_flow_integration():
    """测试核心数据流集成"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_core_flow",
        source="cls",
        title="江丰电子：公司正在韩国建设先进制程靶材生产基地",
        content="江丰电子在韩国建设靶材生产基地",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_core_flow",
        action="candidate",
        need_ai=True,
        pre_score=70,
        matched_keywords=["建设", "生产基地"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    # AI原始输出（模拟）
    ai_result = AIEventResult(
        news_id="test_core_flow",
        is_market_relevant=True,
        event_type="general",
        theme="江丰电子",  # AI错误输出公司名
        sub_themes=[],
        related_stocks=[],
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.6
    )

    # 后处理
    result = processor.process(news, filter_result, ai_result)

    # 验证基础修正
    assert result.event_type == "capacity_build"
    assert result.event_level == "B"

    # 验证主题标准化
    assert result.primary_theme_id == "semiconductor_material"
    assert result.primary_theme_name == "半导体材料"
    assert result.raw_themes == "江丰电子"

    # 验证股票补充
    assert len(result.related_stocks) >= 1
    stock_codes = [s.code for s in result.related_stocks]
    assert "300666.SZ" in stock_codes

    # 验证市场映射
    assert len(result.related_indices) > 0 or len(result.related_etfs) > 0

    # 验证评分
    assert result.final_score > 0
    assert result.trade_priority in ["urgent", "high", "candidate", "watch"]

    print(f"\n✅ 核心数据流测试通过")
    print(f"  event_type: {result.event_type}")
    print(f"  primary_theme: {result.primary_theme_name} ({result.primary_theme_id})")
    print(f"  related_stocks: {[f'{s.name}({s.code})' for s in result.related_stocks]}")
    print(f"  final_score: {result.final_score:.1f}")
    print(f"  trade_priority: {result.trade_priority}")


def test_validator_field_type_check():
    """测试Validator字段类型严格校验"""
    from fund_quant.nlp.news_ai.ai_result_validator import AIResultValidator
    import json

    validator = AIResultValidator()

    news = NewsItem(
        news_id="test_validator",
        source="cls",
        title="测试新闻",
        content="测试内容",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_validator",
        action="candidate",
        need_ai=True,
        pre_score=70,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    # 测试1：AI把positive填到event_level
    bad_response_1 = json.dumps({
        "event_type": "order_win",
        "sentiment": "neutral",
        "event_level": "positive",  # 错误：应该是S/A/B/C
        "theme": "半导体",
        "sub_themes": [],
        "related_stocks": [],
        "novelty_type": "old_theme_new_progress",
        "summary": "测试",
        "confidence": 0.8
    })

    result1 = validator.validate(news, filter_result, bad_response_1)
    assert result1.event_level == "C"  # 应该被修正为C
    assert result1.sentiment == "positive"  # 应该被移动到sentiment
    assert any("event_level错误填写" in err for err in result1.validation_errors)

    print(f"\n✅ Validator字段类型校验测试通过")


def test_stock_entity_validation():
    """测试related_stocks必须包含name/code/reason"""
    from fund_quant.nlp.news_ai.ai_result_validator import AIResultValidator
    import json

    validator = AIResultValidator()

    news = NewsItem(
        news_id="test_stocks",
        source="cls",
        title="测试",
        content="测试",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_stocks",
        action="candidate",
        need_ai=True,
        pre_score=70,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    # related_stocks缺少字段
    bad_response = json.dumps({
        "event_type": "order_win",
        "sentiment": "positive",
        "event_level": "A",
        "theme": "半导体",
        "sub_themes": [],
        "related_stocks": [
            {"name": "江丰电子", "code": ""},  # 缺少code和reason
            {"name": "中国", "code": "CN", "reason": "国家"}  # 非股票实体
        ],
        "novelty_type": "old_theme_new_progress",
        "summary": "测试",
        "confidence": 0.8
    })

    result = validator.validate(news, filter_result, bad_response)

    # 应该删除不合法的stock
    assert len(result.related_stocks) == 0
    assert any("缺少必填字段" in err or "非股票实体" in err for err in result.validation_errors)

    print(f"\n✅ 股票实体校验测试通过")


if __name__ == "__main__":
    test_core_data_flow_integration()
    test_validator_field_type_check()
    test_stock_entity_validation()
    print(f"\n🎉 所有核心数据流测试通过！")
