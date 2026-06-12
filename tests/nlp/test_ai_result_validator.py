"""
AI 结果验证器测试
"""
import json
import pytest
from datetime import datetime

from fund_quant.nlp.news_filter.filter_models import NewsItem, FilterResult
from fund_quant.nlp.news_ai import AIResultValidator


@pytest.fixture
def validator():
    """创建验证器实例"""
    return AIResultValidator()


@pytest.fixture
def sample_news():
    """示例新闻"""
    return NewsItem(
        news_id="test_001",
        source="cls",
        title="测试新闻",
        content="测试内容",
        publish_time=datetime.now()
    )


@pytest.fixture
def sample_filter_result():
    """示例过滤结果"""
    return FilterResult(
        news_id="test_001",
        action="analyze",
        need_ai=True,
        pre_score=85
    )


def test_valid_json(validator, sample_news, sample_filter_result):
    """测试：合法 JSON → is_valid=True"""
    valid_response = json.dumps({
        "is_market_relevant": True,
        "event_type": "sample_delivery",
        "theme": "英伟达M10材料",
        "sub_themes": ["高速PCB"],
        "related_stocks": [
            {"code": "600183.SH", "name": "生益科技", "reason": "送样"}
        ],
        "sentiment": "positive",
        "event_level": "A",
        "novelty_type": "old_theme_new_progress",
        "summary": "测试摘要",
        "confidence": 0.86,
        "risk_flags": []
    }, ensure_ascii=False)

    result = validator.validate(sample_news, sample_filter_result, valid_response)

    assert result.is_valid is True
    assert result.event_type == "sample_delivery"
    assert result.sentiment == "positive"
    assert result.confidence == 0.86
    assert len(result.validation_errors) == 0


def test_invalid_json(validator, sample_news, sample_filter_result):
    """测试：非 JSON → is_valid=False"""
    invalid_response = "这不是一个有效的JSON"

    result = validator.validate(sample_news, sample_filter_result, invalid_response)

    assert result.is_valid is False
    assert "JSON解析失败" in result.validation_errors[0]
    assert result.event_type == "general"
    assert result.confidence == 0.0


def test_invalid_sentiment(validator, sample_news, sample_filter_result):
    """测试：非法 sentiment → is_valid=False"""
    response = json.dumps({
        "is_market_relevant": True,
        "event_type": "sample_delivery",
        "theme": "测试主题",
        "sub_themes": [],
        "related_stocks": [],
        "sentiment": "invalid_sentiment",  # 非法值
        "event_level": "A",
        "novelty_type": "old_theme_new_progress",
        "summary": "测试",
        "confidence": 0.8,
        "risk_flags": []
    })

    result = validator.validate(sample_news, sample_filter_result, response)

    assert result.is_valid is False
    assert any("非法 sentiment" in err for err in result.validation_errors)


def test_invalid_event_level(validator, sample_news, sample_filter_result):
    """测试：非法 event_level → is_valid=False"""
    response = json.dumps({
        "is_market_relevant": True,
        "event_type": "sample_delivery",
        "theme": "测试主题",
        "sub_themes": [],
        "related_stocks": [],
        "sentiment": "positive",
        "event_level": "X",  # 非法值
        "novelty_type": "old_theme_new_progress",
        "summary": "测试",
        "confidence": 0.8,
        "risk_flags": []
    })

    result = validator.validate(sample_news, sample_filter_result, response)

    assert result.is_valid is False
    assert any("非法 event_level" in err for err in result.validation_errors)


def test_invalid_event_type(validator, sample_news, sample_filter_result):
    """测试：非法 event_type → is_valid=False"""
    response = json.dumps({
        "is_market_relevant": True,
        "event_type": "invalid_type",  # 不在白名单中
        "theme": "测试主题",
        "sub_themes": [],
        "related_stocks": [],
        "sentiment": "positive",
        "event_level": "A",
        "novelty_type": "old_theme_new_progress",
        "summary": "测试",
        "confidence": 0.8,
        "risk_flags": []
    })

    result = validator.validate(sample_news, sample_filter_result, response)

    assert result.is_valid is False
    assert any("非法 event_type" in err for err in result.validation_errors)


def test_confidence_out_of_range(validator, sample_news, sample_filter_result):
    """测试：confidence > 1 → is_valid=False"""
    response = json.dumps({
        "is_market_relevant": True,
        "event_type": "sample_delivery",
        "theme": "测试主题",
        "sub_themes": [],
        "related_stocks": [],
        "sentiment": "positive",
        "event_level": "A",
        "novelty_type": "old_theme_new_progress",
        "summary": "测试",
        "confidence": 1.5,  # 超出范围
        "risk_flags": []
    })

    result = validator.validate(sample_news, sample_filter_result, response)

    assert result.is_valid is False
    assert any("confidence 超出范围" in err for err in result.validation_errors)


def test_risk_news_positive_sentiment(validator, sample_news):
    """测试：risk 新闻被判断为 positive → is_valid=False"""
    risk_filter_result = FilterResult(
        news_id="test_001",
        action="risk",
        need_ai=True,
        pre_score=90,
        risk_flags=["澄清"]
    )

    response = json.dumps({
        "is_market_relevant": True,
        "event_type": "risk_disconfirm",
        "theme": "测试主题",
        "sub_themes": [],
        "related_stocks": [],
        "sentiment": "positive",  # risk 新闻不应该是 positive
        "event_level": "A",
        "novelty_type": "negative_disconfirm",
        "summary": "测试",
        "confidence": 0.8,
        "risk_flags": []
    })

    result = validator.validate(sample_news, risk_filter_result, response)

    assert result.is_valid is False
    assert any("risk新闻不应被判断为positive" in err for err in result.validation_errors)


def test_json_code_block_parsing(validator, sample_news, sample_filter_result):
    """测试：AI 返回 ```json ... ``` 代码块时可以正确解析"""
    response_with_code_block = """```json
{
  "is_market_relevant": true,
  "event_type": "sample_delivery",
  "theme": "英伟达M10材料",
  "sub_themes": ["高速PCB"],
  "related_stocks": [
    {"code": "600183.SH", "name": "生益科技", "reason": "送样"}
  ],
  "sentiment": "positive",
  "event_level": "A",
  "novelty_type": "old_theme_new_progress",
  "summary": "测试摘要",
  "confidence": 0.86,
  "risk_flags": []
}
```"""

    result = validator.validate(sample_news, sample_filter_result, response_with_code_block)

    assert result.is_valid is True
    assert result.event_type == "sample_delivery"
    assert result.theme == "英伟达M10材料"


def test_related_stocks_missing_code_warning(validator, sample_news, sample_filter_result):
    """测试：related_stocks 缺 code 不崩溃，但 validation_errors 有 warning"""
    response = json.dumps({
        "is_market_relevant": True,
        "event_type": "sample_delivery",
        "theme": "测试主题",
        "sub_themes": [],
        "related_stocks": [
            {"name": "生益科技", "reason": "送样"}  # 缺少 code
        ],
        "sentiment": "positive",
        "event_level": "A",
        "novelty_type": "old_theme_new_progress",
        "summary": "测试",
        "confidence": 0.8,
        "risk_flags": []
    })

    result = validator.validate(sample_news, sample_filter_result, response)

    # 不崩溃，但有警告
    assert result.is_valid is True  # 缺 code 不是致命错误
    assert len(result.related_stocks) == 1
    assert result.related_stocks[0].code == ""  # 用空字符串填充
    assert result.related_stocks[0].name == "生益科技"
    assert any("缺少 code" in err for err in result.validation_errors)


def test_missing_required_fields(validator, sample_news, sample_filter_result):
    """测试：缺少核心必填字段 → is_valid=False"""
    response = json.dumps({
        "is_market_relevant": True,
        "event_type": "sample_delivery"
        # 缺少其他核心字段：sentiment, event_level, novelty_type
    })

    result = validator.validate(sample_news, sample_filter_result, response)

    assert result.is_valid is False
    assert len(result.validation_errors) > 0
    assert any("缺少核心必填字段" in err for err in result.validation_errors)


def test_invalid_novelty_type(validator, sample_news, sample_filter_result):
    """测试：非法 novelty_type → is_valid=False"""
    response = json.dumps({
        "is_market_relevant": True,
        "event_type": "sample_delivery",
        "theme": "测试主题",
        "sub_themes": [],
        "related_stocks": [],
        "sentiment": "positive",
        "event_level": "A",
        "novelty_type": "invalid_novelty",  # 非法值
        "summary": "测试",
        "confidence": 0.8,
        "risk_flags": []
    })

    result = validator.validate(sample_news, sample_filter_result, response)

    assert result.is_valid is False
    assert any("非法 novelty_type" in err for err in result.validation_errors)
