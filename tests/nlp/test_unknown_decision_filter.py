"""
测试 UnknownDecisionFilter（优化版）
"""
import pytest
from datetime import datetime
from fund_quant.nlp.news_filter import NewsItem, FilterResult, UnknownDecisionFilter


def test_nuclear_wastewater_filtered():
    """日本核污染水排海异常警报停止 → need_ai=False"""
    filter = UnknownDecisionFilter()

    news = NewsItem(
        news_id="test_001",
        source="cls",
        title="日本核污染水排海再次因异常警报停止",
        content="日本核污染水排海作业因异常警报再次停止",
        publish_time=datetime.now()
    )

    original_result = FilterResult(
        news_id="test_001",
        action="unknown",
        need_ai=True,
        pre_score=50,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    refined_result = filter.refine(news, original_result)

    assert refined_result.need_ai is False
    assert any("噪音" in r or "地缘" in r for r in refined_result.reasons)


def test_cross_strait_policy_filtered():
    """两岸交流合作政策措施签约会 → need_ai=False"""
    filter = UnknownDecisionFilter()

    news = NewsItem(
        news_id="test_002",
        source="cls",
        title="十项促进两岸交流合作的政策措施对接签约会在厦门举行",
        content="十项促进两岸交流合作的政策措施在厦门举行对接签约会",
        publish_time=datetime.now()
    )

    original_result = FilterResult(
        news_id="test_002",
        action="unknown",
        need_ai=True,
        pre_score=50,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    refined_result = filter.refine(news, original_result)

    # 只有弱信号（政策、合作），不应该进AI
    assert refined_result.need_ai is False


def test_investor_count_filtered():
    """A股投资者已超2.5亿 → need_ai=False"""
    filter = UnknownDecisionFilter()

    news = NewsItem(
        news_id="test_003",
        source="cls",
        title="A股投资者已超2.5亿",
        content="统计显示A股投资者数量已经超过2.5亿",
        publish_time=datetime.now()
    )

    original_result = FilterResult(
        news_id="test_003",
        action="unknown",
        need_ai=True,
        pre_score=50,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    refined_result = filter.refine(news, original_result)

    assert refined_result.need_ai is False


def test_jiangfeng_electronics_base_passed():
    """江丰电子：公司正在韩国建设先进制程靶材生产基地 - 应该进入AI（强信号）"""
    filter = UnknownDecisionFilter()

    news = NewsItem(
        news_id="test_004",
        source="cls",
        title="江丰电子：公司正在韩国建设先进制程靶材生产基地",
        content="江丰电子公司在韩国建设先进制程靶材生产基地项目",
        publish_time=datetime.now()
    )

    original_result = FilterResult(
        news_id="test_004",
        action="unknown",
        need_ai=False,
        pre_score=30,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    refined_result = filter.refine(news, original_result)

    assert refined_result.need_ai is True
    assert refined_result.pre_score >= 60
    assert any("强交易信号" in r for r in refined_result.reasons)


def test_jd_health_cooperation_passed():
    """京东健康与北京友谊医院达成合作建设大模型 - 应该进入AI（强信号：大模型）"""
    filter = UnknownDecisionFilter()

    news = NewsItem(
        news_id="test_005",
        source="cls",
        title="京东健康与北京友谊医院达成合作 将共同建设消化系统专科大模型",
        content="京东健康与医院合作建设AI大模型",
        publish_time=datetime.now()
    )

    original_result = FilterResult(
        news_id="test_005",
        action="unknown",
        need_ai=False,
        pre_score=30,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    refined_result = filter.refine(news, original_result)

    assert refined_result.need_ai is True
    assert refined_result.pre_score >= 60


def test_empty_title_and_content_archived():
    """标题和正文都为空 - 应该归档"""
    filter = UnknownDecisionFilter()

    news = NewsItem(
        news_id="test_006",
        source="cls",
        title="",
        content="",
        publish_time=datetime.now()
    )

    original_result = FilterResult(
        news_id="test_006",
        action="unknown",
        need_ai=True,
        pre_score=50,
        matched_keywords=[],
        matched_rules=[],
        reasons=[],
        risk_flags=[]
    )

    refined_result = filter.refine(news, original_result)

    assert refined_result.action == "archive"
    assert refined_result.need_ai is False
    assert refined_result.pre_score == 0


def test_non_unknown_action_unchanged():
    """非 unknown 的 action 不应该被修改"""
    filter = UnknownDecisionFilter()

    news = NewsItem(
        news_id="test_007",
        source="cls",
        title="测试新闻",
        content="测试内容",
        publish_time=datetime.now()
    )

    original_result = FilterResult(
        news_id="test_007",
        action="candidate",
        need_ai=True,
        pre_score=70,
        matched_keywords=["中标"],
        matched_rules=["strong_event"],
        reasons=["命中强事件关键词"],
        risk_flags=[]
    )

    refined_result = filter.refine(news, original_result)

    # 应该原样返回
    assert refined_result.action == "candidate"
    assert refined_result.need_ai is True
    assert refined_result.pre_score == 70
