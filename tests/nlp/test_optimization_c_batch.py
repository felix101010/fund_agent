"""
测试关键场景修复（C批优化）
验证：光波导主题、展会过滤、变压器主题、徐工机械股票补全、数据集评分
"""
import pytest
from datetime import datetime
from fund_quant.nlp.news_filter import NewsItem, FilterResult
from fund_quant.nlp.news_ai.ai_event_models import AIEventResult, RelatedStock
from fund_quant.nlp.news_ai.ai_output_post_processor_enhanced import AIOutputPostProcessor


def test_optical_waveguide_not_nev():
    """光波导投产不能映射新能源车"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_waveguide",
        source="cls",
        title="全球首条百万片级体全息光波导自动化产线在天津投产",
        content="尼卡光学(天津)有限公司全球首条百万片级体全息光波导自动化产线投产",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_waveguide",
        action="candidate",
        need_ai=True,
        pre_score=75,
        matched_keywords=["投产", "全球首条"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_waveguide",
        is_market_relevant=True,
        event_type="mass_production",
        theme="消费电子",
        sub_themes=[],
        related_stocks=[],
        sentiment="positive",
        event_level="A",
        novelty_type="new_theme",
        summary="",
        confidence=0.8
    )

    result = processor.process(news, filter_result, ai_result)

    # 验证主题
    assert result.primary_theme_id == "xr_optics" or result.primary_theme_id == "consumer_electronics"
    assert result.primary_theme_id != "new_energy_vehicle"
    # 验证优先级
    assert result.trade_priority != "urgent"

    print(f"\n✅ 光波导主题测试通过: {result.primary_theme_name} ({result.primary_theme_id})")
    print(f"  trade_priority: {result.trade_priority}")


def test_trade_fair_no_theme_mapping():
    """上交会意向成交不能映射具体产业主题"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_fair",
        source="cls",
        title="上交会闭幕 意向成交项目数突破600项",
        content="上交会意向成交项目数突破600项",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_fair",
        action="unknown",
        need_ai=True,
        pre_score=40,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_fair",
        is_market_relevant=False,
        event_type="trade_fair_result",
        theme="",
        sub_themes=[],
        related_stocks=[],
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.3
    )

    result = processor.process(news, filter_result, ai_result)

    # 验证
    assert result.trade_priority == "watch"
    assert len(result.related_etfs) == 0
    assert len(result.related_indices) == 0

    print(f"\n✅ 展会过滤测试通过")
    print(f"  trade_priority: {result.trade_priority}")
    print(f"  related_etfs: {result.related_etfs}")


def test_transformer_theme():
    """变压器订单涨价应映射电网设备"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_transformer",
        source="cls",
        title="头部变压器企业普遍在手订单饱满 部分企业已上调产品价格",
        content="头部变压器企业普遍在手订单饱满，部分企业已上调产品价格，部分订单尚未形成收入",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_transformer",
        action="candidate",
        need_ai=True,
        pre_score=70,
        matched_keywords=["涨价", "订单"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_transformer",
        is_market_relevant=True,
        event_type="price_increase",
        theme="电力设备",
        sub_themes=[],
        related_stocks=[],
        sentiment="positive",
        event_level="A",
        novelty_type="old_theme_new_progress",
        summary="",
        confidence=0.8
    )

    result = processor.process(news, filter_result, ai_result)

    # 验证主题
    assert result.primary_theme_id == "power_grid_equipment"
    # 验证风险标记
    assert "not_recognized_revenue" in result.risk_flags
    # 验证优先级
    assert result.trade_priority == "high" or result.trade_priority == "candidate"

    print(f"\n✅ 变压器主题测试通过: {result.primary_theme_name}")
    print(f"  risk_flags: {result.risk_flags}")
    print(f"  trade_priority: {result.trade_priority}")


def test_xuzhou_stock_completion():
    """徐工机械股票自动补全"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_xuzhou",
        source="cls",
        title="徐工机械：预计今年国内新能源工程机械市场规模达800亿元",
        content="徐工机械预计今年国内新能源工程机械市场规模达800亿元",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_xuzhou",
        action="candidate",
        need_ai=True,
        pre_score=60,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_xuzhou",
        is_market_relevant=True,
        event_type="general",
        theme="工程机械",
        sub_themes=[],
        related_stocks=[],  # AI没识别出
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.5
    )

    result = processor.process(news, filter_result, ai_result)

    # 验证股票补全
    assert len(result.related_stocks) >= 1
    stock_names = [s.name for s in result.related_stocks]
    stock_codes = [s.code for s in result.related_stocks]
    assert "徐工机械" in stock_names
    assert "000425.SZ" in stock_codes

    print(f"\n✅ 徐工机械股票补全测试通过")
    print(f"  related_stocks: {[(s.name, s.code) for s in result.related_stocks]}")


def test_robot_dataset_scoring():
    """机器人数据集基准发布不能high"""
    processor = AIOutputPostProcessor()

    news = NewsItem(
        news_id="test_dataset",
        source="cls",
        title="北京大学联合上纬启元研究院发布家庭服务机器人用户习惯数据集基准",
        content="北京大学联合上纬启元研究院发布家庭服务机器人用户习惯数据集基准",
        publish_time=datetime.now()
    )

    filter_result = FilterResult(
        news_id="test_dataset",
        action="candidate",
        need_ai=True,
        pre_score=60,
        matched_keywords=["发布"],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    ai_result = AIEventResult(
        news_id="test_dataset",
        is_market_relevant=True,
        event_type="benchmark_release",
        theme="机器人",
        sub_themes=[],
        related_stocks=[],
        sentiment="neutral",
        event_level="B",
        novelty_type="new_theme",
        summary="",
        confidence=0.7
    )

    result = processor.process(news, filter_result, ai_result)

    # 验证主题
    assert result.primary_theme_id == "robot"
    # 验证评分
    assert result.final_score <= 72
    assert result.trade_priority == "candidate" or result.trade_priority == "watch"

    print(f"\n✅ 机器人数据集评分测试通过")
    print(f"  final_score: {result.final_score:.1f}")
    print(f"  trade_priority: {result.trade_priority}")


if __name__ == "__main__":
    test_optical_waveguide_not_nev()
    test_trade_fair_no_theme_mapping()
    test_transformer_theme()
    test_xuzhou_stock_completion()
    test_robot_dataset_scoring()
    print(f"\n🎉 所有C批优化测试通过！")
