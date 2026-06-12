"""
AI 输出后处理器测试
"""
import pytest

from fund_quant.nlp.news_ai.ai_output_post_processor import AIOutputPostProcessor


@pytest.fixture
def processor():
    """创建后处理器实例"""
    return AIOutputPostProcessor()


def test_normalize_event_level_standard(processor):
    """测试：标准 event_level 保持不变"""
    assert processor.normalize_event_level("A") == "A"
    assert processor.normalize_event_level("B") == "B"
    assert processor.normalize_event_level("C") == "C"


def test_normalize_event_level_with_suffix(processor):
    """测试：'B级' -> 'B'"""
    assert processor.normalize_event_level("B级") == "B"
    assert processor.normalize_event_level("A级") == "A"
    assert processor.normalize_event_level("C级") == "C"


def test_normalize_event_level_slash(processor):
    """测试：'B/C' -> 'B'（优先高级别）"""
    assert processor.normalize_event_level("B/C") == "B"
    assert processor.normalize_event_level("A/B") == "A"


def test_normalize_event_level_with_prefix(processor):
    """测试：'Level B' -> 'B'"""
    assert processor.normalize_event_level("Level B") == "B"
    assert processor.normalize_event_level("中等/B") == "B"


def test_normalize_sentiment_standard(processor):
    """测试：标准 sentiment"""
    assert processor.normalize_sentiment("positive") == "positive"
    assert processor.normalize_sentiment("negative") == "negative"
    assert processor.normalize_sentiment("neutral") == "neutral"


def test_normalize_sentiment_chinese(processor):
    """测试：中文 sentiment"""
    assert processor.normalize_sentiment("利好") == "positive"
    assert processor.normalize_sentiment("利空") == "negative"
    assert processor.normalize_sentiment("中性") == "neutral"


def test_correct_sentiment_for_sample_delivery(processor):
    """测试：标题包含'送样'，AI 输出 neutral，最终 positive"""
    text = "生益科技：M10覆铜板已送样英伟达"
    sentiment, corrections = processor.correct_sentiment_by_rules(text, "neutral")

    assert sentiment == "positive"
    assert "sentiment_corrected_by_keyword" in corrections


def test_correct_sentiment_for_mass_production(processor):
    """测试：标题包含'量产'，AI 输出 neutral，最终 positive"""
    text = "中兴通讯：800G光模块已实现量产"
    sentiment, corrections = processor.correct_sentiment_by_rules(text, "neutral")

    assert sentiment == "positive"
    assert "sentiment_corrected_by_keyword" in corrections


def test_correct_sentiment_for_clarification(processor):
    """测试：标题包含'澄清''暂无'，AI 输出 positive，最终 negative"""
    text = "某公司澄清：暂无相关人形机器人业务"
    sentiment, corrections = processor.correct_sentiment_by_rules(text, "positive")

    assert sentiment == "negative"
    assert "sentiment_corrected_by_keyword" in corrections


def test_normalize_themes_empty_string(processor):
    """测试：AI 输出 themes=""，最终 themes=[]，不报错"""
    assert processor.normalize_themes("") == []
    assert processor.normalize_themes(None) == []


def test_normalize_themes_single_string(processor):
    """测试：themes="PCB" -> ["PCB"]"""
    assert processor.normalize_themes("PCB") == ["PCB"]


def test_normalize_themes_comma_separated(processor):
    """测试：themes="PCB,英伟达供应链" -> ["PCB", "英伟达供应链"]"""
    result = processor.normalize_themes("PCB,英伟达供应链")
    assert result == ["PCB", "英伟达供应链"]


def test_normalize_themes_list_with_empty(processor):
    """测试：["PCB", "", None] -> ["PCB"]"""
    result = processor.normalize_themes(["PCB", "", None])
    assert result == ["PCB"]


def test_extract_themes_nvidia(processor):
    """测试：'M10覆铜板已送样英伟达' 识别主题"""
    text = "生益科技：M10覆铜板已送样英伟达，等待验证结果"
    themes = processor.extract_themes_by_keywords(text)

    assert "英伟达供应链" in themes
    assert "PCB" in themes


def test_extract_themes_optical_module(processor):
    """测试：'800G光模块' 识别主题"""
    text = "中兴通讯：800G光模块已实现量产"
    themes = processor.extract_themes_by_keywords(text)

    assert "光模块" in themes


def test_extract_themes_robot(processor):
    """测试：'人形机器人' 识别主题"""
    text = "某公司澄清：暂无相关人形机器人业务"
    themes = processor.extract_themes_by_keywords(text)

    assert "机器人" in themes


def test_normalize_event_type_sample_delivery(processor):
    """测试：'送样' -> sample_delivery"""
    event_type = processor.normalize_event_type("", "生益科技已送样英伟达")
    assert event_type == "sample_delivery"


def test_normalize_event_type_mass_production(processor):
    """测试：'量产' -> mass_production"""
    event_type = processor.normalize_event_type("", "800G光模块已实现量产")
    assert event_type == "mass_production"


def test_normalize_event_type_clarification(processor):
    """测试：'澄清：暂无' -> risk_disconfirm"""
    event_type = processor.normalize_event_type("", "某公司澄清：暂无相关人形机器人业务")
    assert event_type == "risk_disconfirm"


def test_confidence_in_range(processor):
    """测试：confidence 必须在 0.0 ~ 1.0"""
    confidence = processor.calculate_confidence(
        raw_confidence=0.7,
        ai_result={"event_type": "sample_delivery"},
        corrections=[],
        event_type="sample_delivery",
        sentiment="positive",
        themes=["PCB"]
    )

    assert 0.0 <= confidence <= 1.0


def test_full_process_sample_delivery(processor):
    """测试：完整流程 - 送样新闻"""
    title = "生益科技：M10覆铜板已送样英伟达，等待验证结果"
    ai_result = {
        "event_type": "unknown",
        "event_level": "B级",
        "sentiment": "neutral",
        "themes": "",
        "confidence": "70%"
    }

    result = processor.process(title, None, ai_result)

    assert result["event_type"] == "sample_delivery"
    assert result["event_level"] == "B"
    assert result["sentiment"] == "positive"
    assert "英伟达供应链" in result["themes"]
    assert "PCB" in result["themes"]
    assert result["confidence"] >= 0.6
    assert len(result["corrections"]) > 0


def test_full_process_mass_production(processor):
    """测试：完整流程 - 量产新闻"""
    title = "中兴通讯：800G光模块已实现量产"
    ai_result = {
        "event_level": "B/C",
        "sentiment": "neutral",
        "themes": []
    }

    result = processor.process(title, None, ai_result)

    assert result["event_type"] == "mass_production"
    assert result["event_level"] == "B"
    assert result["sentiment"] == "positive"
    assert "光模块" in result["themes"]


def test_full_process_clarification(processor):
    """测试：完整流程 - 澄清新闻"""
    title = "某公司澄清：暂无相关人形机器人业务"
    ai_result = {
        "event_level": "B",
        "sentiment": "positive",
        "themes": ["机器人"]
    }

    result = processor.process(title, None, ai_result)

    assert result["event_type"] == "risk_disconfirm"
    assert result["sentiment"] == "negative"
    assert "机器人" in result["themes"]


def test_merge_themes_priority(processor):
    """测试：themes 合并优先级"""
    rule_themes = ["英伟达供应链", "PCB"]
    ai_themes = []
    keyword_themes = ["光模块"]

    result = processor.merge_themes(rule_themes, ai_themes, keyword_themes)

    # 规则主题优先
    assert result[0] == "英伟达供应链"
    assert result[1] == "PCB"
    assert result[2] == "光模块"


def test_parse_confidence_percentage(processor):
    """测试：解析百分比 confidence"""
    assert processor._parse_confidence("70%") == 0.7
    assert processor._parse_confidence("85%") == 0.85
    assert processor._parse_confidence(70) == 0.7
    assert processor._parse_confidence(0.85) == 0.85
