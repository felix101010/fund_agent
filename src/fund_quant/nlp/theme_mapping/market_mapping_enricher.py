"""
市场映射增强器
根据主题补充ETF/指数/股票池信息
"""
from typing import Any
from fund_quant.nlp.theme_mapping.theme_normalizer import ThemeNormalizer


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class MarketMappingEnricher:
    """
    市场映射增强器

    职责：
    1. 根据primary_theme_id补充related_indices、related_etfs
    2. 如果没有明确上市公司，输出candidate_stock_pool_theme
    3. 不硬编股票，只提供主题相关的ETF/指数
    """

    def __init__(self, theme_normalizer: ThemeNormalizer = None):
        """初始化增强器"""
        self.theme_normalizer = theme_normalizer or ThemeNormalizer()

    def enrich(self, ai_event_result: Any, normalized_theme_result: dict) -> dict:
        """
        增强市场映射

        Args:
            ai_event_result: AI事件结果对象
            normalized_theme_result: ThemeNormalizer的输出

        Returns:
            {
                'related_indices': list[str],
                'related_etfs': list[str],
                'candidate_stock_pool_theme': str,
                'enrichment_notes': list[str]
            }
        """
        enrichment_notes = []
        related_indices = []
        related_etfs = []
        candidate_stock_pool_theme = None

        # 获取主主题
        primary_theme_id = normalized_theme_result.get('primary_theme_id')
        primary_theme_name = normalized_theme_result.get('primary_theme_name')
        normalized_themes = normalized_theme_result.get('normalized_themes', [])

        # 获取related_stocks
        related_stocks = get_field(ai_event_result, 'related_stocks', [])

        # 获取event_type
        event_type = get_field(ai_event_result, 'event_type', '')

        # 展会/意向成交类新闻不补充ETF/指数
        if event_type in ['trade_fair_result', 'industry_activity']:
            enrichment_notes.append(f"展会/行业活动类新闻({event_type})，不补充ETF/指数")
            return {
                'related_indices': [],
                'related_etfs': [],
                'candidate_stock_pool_theme': None,
                'enrichment_notes': enrichment_notes
            }

        # 如果有主题，补充指数和ETF
        if normalized_themes:
            for theme in normalized_themes:
                # 主题过滤：根据primary_theme_id过滤不相关的ETF
                theme_id = theme.theme_id

                # battery_material只映射电池/锂电相关，排除医药
                if primary_theme_id == 'battery_material':
                    # 如果当前theme不是battery_material相关，跳过其ETF
                    if theme_id in ['innovative_drug', 'ai_medical']:
                        enrichment_notes.append(f"跳过非电池材料相关主题ETF: {theme.canonical_name}")
                        continue

                # 只添加相关的指数和ETF
                related_indices.extend(theme.index_codes)
                related_etfs.extend(theme.etf_codes)

            # 去重
            related_indices = list(set(related_indices))
            related_etfs = list(set(related_etfs))

            if related_indices:
                enrichment_notes.append(f"补充相关指数: {', '.join(related_indices)}")
            if related_etfs:
                enrichment_notes.append(f"补充相关ETF: {', '.join(related_etfs)}")

        # 如果没有明确股票，但有主题，输出候选股票池主题
        if not related_stocks and primary_theme_name:
            candidate_stock_pool_theme = primary_theme_name
            enrichment_notes.append(f"无明确个股，建议关注{primary_theme_name}主题股票池")

        return {
            'related_indices': related_indices,
            'related_etfs': related_etfs,
            'candidate_stock_pool_theme': candidate_stock_pool_theme,
            'enrichment_notes': enrichment_notes
        }


__all__ = ['MarketMappingEnricher']
