"""
简单规则过滤器单元测试
"""
import pytest
from datetime import datetime

from fund_quant.nlp.news_filter import NewsItem, FilterResult, SimpleRuleFilter


@pytest.fixture
def filter():
    """创建过滤器实例"""
    return SimpleRuleFilter()


def test_risk_keyword_match(filter):
    """测试：命中"暂无相关业务" → risk，need_ai=True"""
    news = NewsItem(
        news_id="test_001",
        source="cls",
        title="某公司回应：暂无相关业务",
        content="公司澄清，目前暂无相关业务。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "risk"
    assert result.need_ai is True
    assert result.pre_score == 90
    assert "暂无相关业务" in result.matched_keywords
    assert "澄清" in result.matched_keywords
    assert "risk_keywords" in result.matched_rules
    assert len(result.risk_flags) > 0


def test_strong_event_verification_passed(filter):
    """测试：命中"验证通过" → analyze，need_ai=True"""
    news = NewsItem(
        news_id="test_002",
        source="cls",
        title="某芯片公司产品验证通过",
        content="公司宣布，新一代芯片已通过客户验证通过测试。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "analyze"
    assert result.need_ai is True
    assert result.pre_score == 85
    assert "验证通过" in result.matched_keywords
    assert "strong_event_keywords" in result.matched_rules


def test_strong_event_sample(filter):
    """测试：命中"送样" → analyze，need_ai=True"""
    news = NewsItem(
        news_id="test_003",
        source="cls",
        title="PCB公司向英伟达送样",
        content="公司已向英伟达送样M10覆铜板，等待验证结果。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "analyze"
    assert result.need_ai is True
    assert result.pre_score == 85
    assert "送样" in result.matched_keywords
    assert "strong_event_keywords" in result.matched_rules


def test_candidate_new_material(filter):
    """测试：命中"新材料" → candidate，need_ai=True"""
    news = NewsItem(
        news_id="test_004",
        source="cls",
        title="公司研发新材料取得进展",
        content="公司在新材料领域持续投入研发。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "candidate"
    assert result.need_ai is True
    assert result.pre_score == 65
    assert "新材料" in result.matched_keywords
    assert "candidate_keywords" in result.matched_rules


def test_strong_entity_nvidia(filter):
    """测试：命中"英伟达"但无强事件 → candidate，need_ai=True"""
    news = NewsItem(
        news_id="test_005",
        source="cls",
        title="英伟达发布财报",
        content="英伟达发布最新季度财报，营收同比增长。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "candidate"
    assert result.need_ai is True
    assert result.pre_score == 60
    assert "英伟达" in result.matched_keywords
    assert "strong_entity_keywords" in result.matched_rules


def test_strong_event_overrides_low_value(filter):
    """测试：命中"一文看懂"但同时命中"送样" → analyze，不是 low_value"""
    news = NewsItem(
        news_id="test_006",
        source="cls",
        title="一文看懂英伟达M10覆铜板送样进展",
        content="本文详细解读英伟达M10覆铜板送样的最新进展。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    # 强事件优先级高于低价值
    assert result.action == "analyze"
    assert result.need_ai is True
    assert result.pre_score == 85
    assert "送样" in result.matched_keywords
    assert "strong_event_keywords" in result.matched_rules


def test_low_value_expert_opinion(filter):
    """测试：命中"专家表示长期向好" → low_value，need_ai=False"""
    news = NewsItem(
        news_id="test_007",
        source="cls",
        title="专家表示半导体行业长期向好",
        content="业内专家表示，半导体行业长期向好，未来可期。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "low_value"
    assert result.need_ai is False
    assert result.pre_score == 25
    assert "专家表示" in result.matched_keywords
    assert "长期向好" in result.matched_keywords
    assert "未来可期" in result.matched_keywords
    assert "low_value_keywords" in result.matched_rules


def test_junk_entertainment(filter):
    """测试：命中"娱乐明星" → archive，need_ai=False"""
    news = NewsItem(
        news_id="test_008",
        source="other",
        title="娱乐明星参加综艺节目",
        content="某明星参加娱乐综艺节目，收视率创新高。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "archive"
    assert result.need_ai is False
    assert result.pre_score == 5
    assert "娱乐" in result.matched_keywords
    assert "明星" in result.matched_keywords
    assert "综艺" in result.matched_keywords
    assert "junk_keywords" in result.matched_rules


def test_unknown_authoritative_source(filter):
    """测试：无关键词但来源"财联社" → unknown，need_ai=True"""
    news = NewsItem(
        news_id="test_009",
        source="财联社",
        title="市场动态",
        content="今日市场整体平稳运行。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "unknown"
    assert result.need_ai is True
    assert result.pre_score == 40
    assert "authoritative_source" in result.matched_rules
    assert "未命中关键词，但来源权威" in result.reasons[0]


def test_unknown_normal_source(filter):
    """测试：无关键词且普通来源 → unknown，need_ai=False"""
    news = NewsItem(
        news_id="test_010",
        source="普通来源",
        title="市场观察",
        content="今日市场观察报告。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "unknown"
    assert result.need_ai is False
    assert result.pre_score == 30
    assert "unknown_source" in result.matched_rules
    assert "未命中关键词，普通来源" in result.reasons[0]


def test_risk_highest_priority(filter):
    """测试：风险关键词优先级最高"""
    news = NewsItem(
        news_id="test_011",
        source="cls",
        title="公司澄清：未涉及英伟达送样业务",
        content="公司公告澄清，目前未涉及英伟达相关送样业务。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    # 虽然命中"英伟达"和"送样"，但风险关键词优先级最高
    assert result.action == "risk"
    assert result.need_ai is True
    assert result.pre_score == 90
    assert "澄清" in result.matched_keywords
    assert "未涉及" in result.matched_keywords


def test_multiple_keyword_matches(filter):
    """测试：记录所有匹配的关键词"""
    news = NewsItem(
        news_id="test_012",
        source="cls",
        title="公司获批新材料项目并签订框架协议",
        content="公司新材料项目获批，与客户签订战略合作框架协议。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    # 应该命中强事件关键词
    assert result.action == "analyze"
    assert "获批" in result.matched_keywords
    assert "框架协议" in result.matched_keywords


def test_source_cls_lowercase(filter):
    """测试：source="cls" 被识别为权威来源"""
    news = NewsItem(
        news_id="test_013",
        source="cls",
        title="市场简报",
        content="今日市场简报。",
        publish_time=datetime.now()
    )

    result = filter.filter(news)

    assert result.action == "unknown"
    assert result.need_ai is True
    assert result.pre_score == 40
