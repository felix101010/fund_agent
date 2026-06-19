"""
股票实体解析器（增强版）
清洗 AI 输出的 related_stocks，从文本中自动补充上市公司，将非股票实体移到 related_entities
"""
import re
from dataclasses import dataclass, field
from typing import Any


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


@dataclass
class RelatedEntity:
    """关联实体（非股票）"""
    name: str
    entity_type: str  # country, person, organization, unknown_entity
    reason: str


@dataclass
class StockResolveResult:
    """股票解析结果"""
    related_stocks: list = field(default_factory=list)
    related_entities: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class StockEntityResolver:
    """
    股票实体解析器（增强版）

    职责：
    1. 清洗 AI 输出的 related_stocks
    2. 从文本中自动补充上市公司
    3. 只保留真正的股票，其他移到 related_entities
    4. 补全缺失的股票代码
    5. 修正错误的股票代码
    """

    # 内置股票映射表
    DEFAULT_SYMBOL_MAP = {
        "生益科技": "600183.SH",
        "沪电股份": "002463.SZ",
        "胜宏科技": "300476.SZ",
        "工业富联": "601138.SH",
        "中际旭创": "300308.SZ",
        "新易盛": "300502.SZ",
        "寒武纪": "688256.SH",
        "中芯国际": "688981.SH",
        "中兴通讯": "000063.SZ",
        "江丰电子": "300666.SZ",
        "包钢股份": "600010.SH",
        "中国人保": "601319.SH",
        "京东健康": "06618.HK",
        "小米集团": "01810.HK",
        "徐工机械": "000425.SZ",
        "海康威视": "002415.SZ",
        "富祥股份": "300497.SZ",
        # 新增公司映射
        "百利天恒": "688506.SH",
        "百奥泰": "688177.SH",
        "立昂微": "605358.SH",
        "拉普拉斯": "688726.SH",
        "松发股份": "603268.SH",
        "普莱柯": "603566.SH",
        "阳谷华泰": "300121.SZ",
        "新金路": "000510.SZ",
        "和远气体": "002971.SZ",
        "电光科技": "002730.SZ",
        "大禹节水": "300021.SZ",
        "中色股份": "000758.SZ",
        "富奥股份": "000030.SZ",
        "英搏尔": "300681.SZ",
    }

    # 公司到默认主题映射
    COMPANY_THEME_MAP = {
        "中际旭创": {
            "code": "300308.SZ",
            "default_theme_id": "optical_module",
            "default_theme_name": "光模块/CPO",
            "aliases": ["中际旭创", "中际旭创股份", "中际旭创股份有限公司"],
            "related_concepts": ["光模块", "CPO", "AI算力", "数据中心", "高速光通信", "800G", "1.6T"]
        },
        "海康威视": {
            "code": "002415.SZ",
            "default_theme_id": "smart_security",
            "default_theme_name": "智能安防",
            "aliases": ["海康威视", "杭州海康威视"],
            "related_concepts": ["智能安防", "AI视觉", "机器视觉", "城市治理", "工业安全"]
        },
        "富祥股份": {
            "code": "300497.SZ",
            "default_theme_id": "battery_material",
            "default_theme_name": "电池材料",
            "aliases": ["富祥股份", "江西富祥"],
            "related_concepts": ["锂电材料", "电解液添加剂", "VC添加剂", "FEC添加剂", "动力电池材料", "电解液"]
        },
    }

    # 非股票实体关键词（国家）
    NON_STOCK_COUNTRIES = {
        "中国", "美国", "伊朗", "以色列", "黎巴嫩", "巴基斯坦", "加蓬", "非洲",
        "俄罗斯", "日本", "韩国", "印度", "欧盟", "英国", "法国", "德国"
    }

    # 机构关键词
    INSTITUTION_KEYWORDS = [
        "商会", "协会", "委员会", "政府", "法院", "司法", "议会",
        "理事会", "联合会", "学会", "研究院", "大学", "基金会",
        "医院", "医疗", "银行", "保险"
    ]

    # 人物关键词
    PERSON_KEYWORDS = [
        "议员", "总监", "副市长", "市长", "部长", "大使", "总统", "总理"
    ]

    def __init__(self, symbol_map: dict = None):
        """
        初始化解析器

        Args:
            symbol_map: 股票名称到代码的映射表，如果为 None 则使用默认映射
        """
        self.symbol_map = symbol_map if symbol_map is not None else self.DEFAULT_SYMBOL_MAP.copy()

    def resolve_company_name(self, name: str) -> dict | None:
        """
        根据公司简称/别名解析股票（新增方法）

        Args:
            name: 公司名称

        Returns:
            {
                "name": "富祥股份",
                "code": "300497.SZ",
                "match_source": "title_rule",
                "match_confidence": 0.95
            } 或 None
        """
        if not name or not isinstance(name, str):
            return None

        name = name.strip()

        # 1. 直接匹配symbol_map
        if name in self.symbol_map:
            return {
                "name": name,
                "code": self.symbol_map[name],
                "match_source": "title_rule",
                "match_confidence": 0.95
            }

        # 2. 匹配COMPANY_THEME_MAP的key或aliases
        for company, info in self.COMPANY_THEME_MAP.items():
            if company == name:
                return {
                    "name": company,
                    "code": info["code"],
                    "match_source": "title_rule",
                    "match_confidence": 0.95
                }
            # 检查aliases
            aliases = info.get("aliases", [])
            if name in aliases:
                return {
                    "name": company,
                    "code": info["code"],
                    "match_source": "title_rule",
                    "match_confidence": 0.90
                }

        # 3. 简称清洗匹配（低优先级）
        cleaned_name = name
        # 去掉常见后缀
        for suffix in ["股份有限公司", "有限公司", "集团", "股份", "科技"]:
            if cleaned_name.endswith(suffix):
                cleaned_name = cleaned_name[:-len(suffix)]
                break

        # 用清洗后的名称再匹配一次
        if cleaned_name != name and cleaned_name in self.symbol_map:
            return {
                "name": cleaned_name,
                "code": self.symbol_map[cleaned_name],
                "match_source": "title_rule",
                "match_confidence": 0.85
            }

        # 4. 无法匹配
        return None

    def get_company_default_theme(self, company_name: str) -> dict:
        """
        获取公司的默认主题

        Args:
            company_name: 公司名称

        Returns:
            {
                "theme_id": "...",
                "theme_name": "...",
                "stock_code": "..."
            } 或 None
        """
        for company, info in self.COMPANY_THEME_MAP.items():
            if company in company_name or any(alias in company_name for alias in info.get("aliases", [])):
                return {
                    "theme_id": info.get("default_theme_id"),
                    "theme_name": info.get("default_theme_name"),
                    "stock_code": info.get("code")
                }
        return None

    def _is_valid_stock_code(self, code: str) -> bool:
        """判断是否为合法股票代码"""
        if not code or not isinstance(code, str):
            return False

        code = code.strip()

        # A股代码：000001.SZ / 600000.SH / 688000.SH / 920000.BJ
        if re.match(r'^[0-9]{6}\.(SH|SZ|BJ)$', code):
            return True

        # 港股代码：00001.HK / 01810.HK
        if re.match(r'^[0-9]{5}\.HK$', code):
            return True

        # 美股代码：NVDA / AAPL / MSFT（1-5位大写字母）
        if re.match(r'^[A-Z]{1,5}$', code):
            return True

        return False

    def _classify_entity(self, name: str) -> tuple[str, str]:
        """
        分类实体类型（优化顺序）

        Returns:
            (entity_category, entity_type)
            - entity_category: "stock" / "non_stock"
            - entity_type: "stock" / "country" / "organization" / "person" / "unknown_entity"
        """
        if not name or not isinstance(name, str):
            return "non_stock", "unknown_entity"

        name = name.strip()

        # 1. 优先判断：symbol_map 中的股票
        if name in self.symbol_map:
            return "stock", "stock"

        # 2. 判断：国家
        if name in self.NON_STOCK_COUNTRIES:
            return "non_stock", "country"

        # 3. 判断：机构（医院、商会等）
        for keyword in self.INSTITUTION_KEYWORDS:
            if keyword in name:
                return "non_stock", "organization"

        # 4. 判断：人物
        for keyword in self.PERSON_KEYWORDS:
            if keyword in name:
                return "non_stock", "person"

        # 5. 判断：2-4个汉字的人名（排除包含公司关键词的）
        if re.match(r'^[一-龥]{2,4}$', name):
            company_keywords = ["公司", "股份", "集团", "科技", "电子", "通讯", "银行", "保险", "健康"]
            if not any(kw in name for kw in company_keywords):
                return "non_stock", "person"

        # 6. 无效值
        if name in ["无", "无关", "未提及"]:
            return "non_stock", "unknown_entity"

        # 7. 其他情况
        return "non_stock", "unknown_entity"

    def resolve_from_text(
        self, title: str, content: str, existing_stocks: list = None
    ) -> StockResolveResult:
        """
        从文本中提取上市公司

        Args:
            title: 新闻标题
            content: 新闻正文
            existing_stocks: 已有的股票列表（避免重复）

        Returns:
            StockResolveResult
        """
        result = StockResolveResult()

        # 合并文本
        text = f"{title} {content}"

        # 收集已有的股票代码和名称（去重）
        existing_codes = set()
        existing_names = set()

        if existing_stocks:
            for stock in existing_stocks:
                code = get_field(stock, 'code', '')
                name = get_field(stock, 'name', '')
                if code:
                    existing_codes.add(code)
                if name:
                    existing_names.add(name)

        # 扫描文本，查找上市公司
        for company_name, stock_code in self.symbol_map.items():
            if company_name in text:
                # 避免重复
                if stock_code in existing_codes or company_name in existing_names:
                    continue

                # 添加到 related_stocks
                from fund_quant.nlp.news_ai.ai_event_models import RelatedStock
                result.related_stocks.append(RelatedStock(
                    name=company_name,
                    code=stock_code,
                    reason="新闻标题/正文中明确提及该上市公司"
                ))

                existing_codes.add(stock_code)
                existing_names.add(company_name)

        return result

    def resolve(self, ai_event_result: Any) -> StockResolveResult:
        """
        解析 AI 事件结果中的 related_stocks

        Args:
            ai_event_result: AI 事件结果对象

        Returns:
            StockResolveResult
        """
        result = StockResolveResult()

        # 获取原始 related_stocks
        original_stocks = get_field(ai_event_result, 'related_stocks', [])

        if not original_stocks:
            return result

        for stock_item in original_stocks:
            # 获取 name 和 code
            if isinstance(stock_item, dict):
                name = stock_item.get('name', '')
                code = stock_item.get('code', '')
                reason = stock_item.get('reason', '')
            else:
                name = getattr(stock_item, 'name', '')
                code = getattr(stock_item, 'code', '')
                reason = getattr(stock_item, 'reason', '')

            name = name.strip() if name else ''
            code = code.strip() if code else ''

            # 分类实体
            entity_category, entity_type = self._classify_entity(name)

            # 如果是股票
            if entity_category == "stock":
                # 在 symbol_map 中
                expected_code = self.symbol_map[name]

                # 补全或修正代码
                if not code:
                    code = expected_code
                    result.warnings.append(f"补全股票代码: {name} → {code}")
                elif code != expected_code:
                    result.warnings.append(f"修正股票代码: {name} {code} → {expected_code}")
                    code = expected_code

                # 保留到 related_stocks
                if isinstance(stock_item, dict):
                    result.related_stocks.append({
                        'name': name,
                        'code': code,
                        'reason': reason
                    })
                else:
                    from fund_quant.nlp.news_ai.ai_event_models import RelatedStock
                    result.related_stocks.append(RelatedStock(
                        name=name,
                        code=code,
                        reason=reason
                    ))
                continue

            # 如果 code 看起来合法，即使不在 symbol_map 中也保留
            if self._is_valid_stock_code(code):
                if isinstance(stock_item, dict):
                    result.related_stocks.append({
                        'name': name,
                        'code': code,
                        'reason': reason
                    })
                else:
                    from fund_quant.nlp.news_ai.ai_event_models import RelatedStock
                    result.related_stocks.append(RelatedStock(
                        name=name,
                        code=code,
                        reason=reason
                    ))
                continue

            # 非股票实体，移到 related_entities
            result.related_entities.append(RelatedEntity(
                name=name,
                entity_type=entity_type,
                reason=reason
            ))

            if entity_type == "unknown_entity":
                result.warnings.append(f"无法确认股票实体: {name}")

        return result


__all__ = ['RelatedEntity', 'StockResolveResult', 'StockEntityResolver']
