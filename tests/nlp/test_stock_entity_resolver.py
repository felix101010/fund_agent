"""
测试 StockEntityResolver（增强版）
"""
import pytest
from fund_quant.nlp.entity_linking import StockEntityResolver, RelatedEntity
from fund_quant.nlp.news_ai.ai_event_models import RelatedStock, AIEventResult


def test_resolve_from_text_jd_health():
    """resolve_from_text: 京东健康与北京友谊医院达成合作 → 京东健康 06618.HK"""
    resolver = StockEntityResolver()

    result = resolver.resolve_from_text(
        title="京东健康与北京友谊医院达成合作 将共同建设消化系统专科大模型",
        content="京东健康与北京友谊医院达成战略合作",
        existing_stocks=None
    )

    assert len(result.related_stocks) == 1
    assert result.related_stocks[0].name == "京东健康"
    assert result.related_stocks[0].code == "06618.HK"
    assert "上市公司" in result.related_stocks[0].reason


def test_resolve_from_text_jiangfeng():
    """resolve_from_text: 江丰电子从正文补入 300666.SZ"""
    resolver = StockEntityResolver()

    result = resolver.resolve_from_text(
        title="公司正在韩国建设先进制程靶材生产基地",
        content="江丰电子在韩国建设靶材生产基地",
        existing_stocks=None
    )

    assert len(result.related_stocks) == 1
    assert result.related_stocks[0].name == "江丰电子"
    assert result.related_stocks[0].code == "300666.SZ"


def test_resolve_from_text_baogang():
    """resolve_from_text: 包钢股份从正文补入 600010.SH"""
    resolver = StockEntityResolver()

    result = resolver.resolve_from_text(
        title="AI炼钢项目投用",
        content="包钢股份的AI炼钢项目正式投用",
        existing_stocks=None
    )

    assert len(result.related_stocks) == 1
    assert result.related_stocks[0].name == "包钢股份"
    assert result.related_stocks[0].code == "600010.SH"


def test_resolve_from_text_no_duplicate():
    """resolve_from_text: 不重复添加已有股票"""
    resolver = StockEntityResolver()

    existing = [
        RelatedStock(name="江丰电子", code="300666.SZ", reason="AI输出")
    ]

    result = resolver.resolve_from_text(
        title="江丰电子建设生产基地",
        content="江丰电子在韩国建设生产基地",
        existing_stocks=existing
    )

    # 不应该重复添加
    assert len(result.related_stocks) == 0


def test_jd_health_is_stock_not_person():
    """京东健康应识别为股票，不是人名"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_jdh",
        is_market_relevant=True,
        event_type="strategic_cooperation",
        theme="AI医疗",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="京东健康", code="", reason="合作主体")
        ],
        sentiment="positive",
        event_level="B",
        novelty_type="old_theme_new_progress",
        summary="",
        confidence=0.8
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 1
    assert resolve_result.related_stocks[0].name == "京东健康"
    assert resolve_result.related_stocks[0].code == "06618.HK"
    assert len(resolve_result.related_entities) == 0  # 不应该在entities中


def test_beijing_hospital_is_organization():
    """北京友谊医院应识别为organization"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_hosp",
        is_market_relevant=True,
        event_type="strategic_cooperation",
        theme="AI医疗",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="北京友谊医院", code="", reason="合作方")
        ],
        sentiment="positive",
        event_level="B",
        novelty_type="old_theme_new_progress",
        summary="",
        confidence=0.8
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 0
    assert len(resolve_result.related_entities) == 1
    assert resolve_result.related_entities[0].name == "北京友谊医院"
    assert resolve_result.related_entities[0].entity_type == "organization"
    """生益科技 code 为空 → 补全 600183.SH"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_001",
        is_market_relevant=True,
        event_type="supply_chain",
        theme="PCB",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="生益科技", code="", reason="进入供应链")
        ],
        sentiment="positive",
        event_level="A",
        novelty_type="old_theme_new_progress",
        summary="生益科技进入供应链",
        confidence=0.85
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 1
    assert resolve_result.related_stocks[0].code == "600183.SH"
    assert resolve_result.related_stocks[0].name == "生益科技"
    assert "补全股票代码" in resolve_result.warnings[0]


def test_jiangfeng_electronics_code_completion():
    """江丰电子 code 为空 → 补全 300666.SZ"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_002",
        is_market_relevant=True,
        event_type="capacity_build",
        theme="半导体材料",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="江丰电子", code="", reason="建设生产基地")
        ],
        sentiment="positive",
        event_level="B",
        novelty_type="old_theme_new_progress",
        summary="江丰电子建设生产基地",
        confidence=0.80
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 1
    assert resolve_result.related_stocks[0].code == "300666.SZ"
    assert resolve_result.related_stocks[0].name == "江丰电子"


def test_country_moved_to_entities():
    """中国 → 移到 related_entities，不保留 related_stocks"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_003",
        is_market_relevant=False,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="中国", code="", reason="国家主体")
        ],
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.3
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 0
    assert len(resolve_result.related_entities) == 1
    assert resolve_result.related_entities[0].name == "中国"
    assert resolve_result.related_entities[0].entity_type == "country"


def test_person_name_moved_to_entities():
    """何逢阳 → 移到 related_entities"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_004",
        is_market_relevant=False,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="何逢阳", code="", reason="人物")
        ],
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.3
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 0
    assert len(resolve_result.related_entities) == 1
    assert resolve_result.related_entities[0].name == "何逢阳"
    assert resolve_result.related_entities[0].entity_type == "person"


def test_association_moved_to_entities():
    """中国摩托车商会 → 移到 related_entities"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_005",
        is_market_relevant=False,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="中国摩托车商会", code="", reason="行业组织")
        ],
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.3
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 0
    assert len(resolve_result.related_entities) == 1
    assert resolve_result.related_entities[0].name == "中国摩托车商会"
    assert resolve_result.related_entities[0].entity_type == "organization"


def test_valid_code_preserved():
    """合法 code="000063.SZ" → 保留"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_006",
        is_market_relevant=True,
        event_type="order_win",
        theme="光模块",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="中兴通讯", code="000063.SZ", reason="中标项目")
        ],
        sentiment="positive",
        event_level="A",
        novelty_type="old_theme_new_progress",
        summary="中兴通讯中标",
        confidence=0.90
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 1
    assert resolve_result.related_stocks[0].code == "000063.SZ"
    assert resolve_result.related_stocks[0].name == "中兴通讯"


def test_code_mismatch_corrected():
    """code 与 symbol_map 不一致 → 使用 symbol_map 并记录 warning"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_007",
        is_market_relevant=True,
        event_type="supply_chain",
        theme="PCB",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="生益科技", code="600000.SH", reason="错误代码")
        ],
        sentiment="positive",
        event_level="A",
        novelty_type="old_theme_new_progress",
        summary="",
        confidence=0.85
    )

    resolve_result = resolver.resolve(result)

    assert len(resolve_result.related_stocks) == 1
    assert resolve_result.related_stocks[0].code == "600183.SH"
    assert any("修正股票代码" in w for w in resolve_result.warnings)


def test_mixed_stocks_and_entities():
    """混合：股票保留，非股票移到 entities"""
    resolver = StockEntityResolver()

    result = AIEventResult(
        news_id="test_008",
        is_market_relevant=True,
        event_type="general",
        theme="",
        sub_themes=[],
        related_stocks=[
            RelatedStock(name="江丰电子", code="", reason="公司"),
            RelatedStock(name="中国", code="", reason="国家"),
            RelatedStock(name="伊朗司法总监", code="", reason="人物"),
            RelatedStock(name="中兴通讯", code="000063.SZ", reason="公司")
        ],
        sentiment="neutral",
        event_level="C",
        novelty_type="noise",
        summary="",
        confidence=0.5
    )

    resolve_result = resolver.resolve(result)

    # 应该有2个股票
    assert len(resolve_result.related_stocks) == 2
    stock_names = [s.name for s in resolve_result.related_stocks]
    assert "江丰电子" in stock_names
    assert "中兴通讯" in stock_names

    # 应该有2个非股票实体
    assert len(resolve_result.related_entities) == 2
    entity_names = [e.name for e in resolve_result.related_entities]
    assert "中国" in entity_names
    assert "伊朗司法总监" in entity_names
