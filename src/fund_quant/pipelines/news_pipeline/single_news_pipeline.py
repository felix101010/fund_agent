"""
单条新闻处理流水线
处理单条 NewsItem，不打印，只返回结果
"""
from typing import Any
from datetime import datetime

from fund_quant.nlp.news_filter import NewsItem, SimpleRuleFilter, UnknownDecisionFilter
from fund_quant.nlp.news_ai import AIEventExtractor
from fund_quant.nlp.entity_linking import TitleCompanyExtractor, StockEntityResolver
from fund_quant.nlp.entity_linking.stock_validator import clean_related_stocks
from fund_quant.nlp.news_filter.paid_content_detector import PaidContentDetector, is_paid_research_teaser, classify_paid_research_teaser
from fund_quant.nlp.news_filter.keyword_rules import (
    extract_stocks_by_code_pattern,
    classify_overseas_ai_infrastructure,
    classify_apple_ai_terminal,
    fix_war_drone_theme,
    apply_ai_level,
)
from fund_quant.pipelines.news_pipeline.pipeline_models import NewsProcessResult


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class SingleNewsPipeline:
    """
    单条新闻处理流水线

    职责：
    1. 规则过滤
    2. Unknown二次过滤
    3. AI事件抽取（need_ai=True时）
    4. 捕获异常，不中断
    5. 返回 NewsProcessResult
    """

    def __init__(self, ai_extractor: AIEventExtractor = None):
        """
        初始化

        Args:
            ai_extractor: AI事件抽取器，如果为None则创建默认实例
        """
        self.rule_filter = SimpleRuleFilter()
        self.unknown_filter = UnknownDecisionFilter()
        self.ai_extractor = ai_extractor or AIEventExtractor()

        # 新增：标题公司名识别和付费内容检测
        self.title_extractor = TitleCompanyExtractor()
        self.stock_resolver = StockEntityResolver()
        self.paid_detector = PaidContentDetector()

    def process(
        self,
        news: NewsItem,
        batch_id: str,
        run_id: str,
        is_new: bool = True
    ) -> NewsProcessResult:
        """
        处理单条新闻

        Args:
            news: 新闻对象
            batch_id: 批次ID
            run_id: 运行ID
            is_new: 是否为新增新闻

        Returns:
            NewsProcessResult
        """
        result = NewsProcessResult(
            batch_id=batch_id,
            run_id=run_id,
            news_id=get_field(news, 'news_id', ''),
            source=get_field(news, 'source', ''),
            title=get_field(news, 'title', ''),
            content=get_field(news, 'content', ''),
            publish_time=get_field(news, 'publish_time', datetime.now()),
            url=get_field(news, 'url', ''),
            is_new=is_new
        )

        # 如果不是新增新闻，跳过处理
        if not is_new:
            result.processing_status = "skipped"
            result.processing_error = "重复新闻"
            return result

        try:
            # === 原有规则过滤（先执行） ===

            # 1. 规则过滤
            filter_result = self.rule_filter.filter(news)
            result.filter_result = filter_result

            # 2. Unknown二次过滤
            action = get_field(filter_result, 'action', 'unknown')
            if action == "unknown":
                unknown_result = self.unknown_filter.refine(news, filter_result)
                result.unknown_refine_result = unknown_result
                filter_result = unknown_result

            # === 增强规则处理（在规则过滤后） ===

            # 0. 构建完整文本（使用 normalized_title）
            title = get_field(news, 'title', '')
            content = get_field(news, 'content', '')
            normalized_title = get_field(news, 'normalized_title', '')
            full_text = f"{normalized_title} {title} {content}"

            # 0.1 硬解析股票代码（规则层提取）
            rule_stocks = extract_stocks_by_code_pattern(full_text)
            if rule_stocks:
                # 将规则层提取的股票注入到 filter_result
                existing_stocks = get_field(filter_result, 'related_stocks', [])
                if not existing_stocks:
                    existing_stocks = []
                # 合并
                stock_codes = {get_field(s, 'code', '') for s in existing_stocks}
                for stock in rule_stocks:
                    if stock['code'] not in stock_codes:
                        existing_stocks.append(stock)
                        stock_codes.add(stock['code'])

                if hasattr(filter_result, 'related_stocks'):
                    filter_result.related_stocks = existing_stocks
                if hasattr(filter_result, 'related_stocks_count'):
                    filter_result.related_stocks_count = len(existing_stocks)

            # 0.2 判断是否付费研报
            if is_paid_research_teaser(full_text):
                # 付费研报特殊处理
                paid_item = {
                    'title': title,
                    'content': content,
                    'normalized_title': normalized_title,
                    'related_stocks': rule_stocks if rule_stocks else []
                }
                paid_result = classify_paid_research_teaser(paid_item)

                # 更新 filter_result
                for key, value in paid_result.items():
                    if hasattr(filter_result, key):
                        setattr(filter_result, key, value)

                # 应用 ai_level
                paid_item_with_level = apply_ai_level(paid_result)
                for key, value in paid_item_with_level.items():
                    if hasattr(filter_result, key):
                        setattr(filter_result, key, value)

            # 0.3 苹果AI终端主题
            apple_item = {
                'title': title,
                'content': content,
                'normalized_title': normalized_title,
            }
            apple_result = classify_apple_ai_terminal(apple_item)
            if apple_result:
                for key, value in apple_result.items():
                    if hasattr(filter_result, key):
                        setattr(filter_result, key, value)

            # 0.4 海外AI基建/软件
            overseas_item = {
                'title': title,
                'content': content,
                'normalized_title': normalized_title,
                'theme_ids': get_field(filter_result, 'theme_ids', []),
                'theme_names': get_field(filter_result, 'theme_names', []),
            }
            overseas_result = classify_overseas_ai_infrastructure(overseas_item)
            if overseas_result:
                for key, value in overseas_result.items():
                    # 特殊处理 theme_ids/theme_names，合并而不是覆盖
                    if key in ['theme_ids', 'theme_names']:
                        existing = get_field(filter_result, key, [])
                        if isinstance(existing, list):
                            for item in value:
                                if item not in existing:
                                    existing.append(item)
                            if hasattr(filter_result, key):
                                setattr(filter_result, key, existing)
                    else:
                        if hasattr(filter_result, key):
                            setattr(filter_result, key, value)

            # 3. 判断是否需要AI
            need_ai = get_field(filter_result, 'need_ai', False)
            result.need_ai = need_ai

            if not need_ai:
                # 即使不需要AI，也要应用后处理
                # 战争无人机修正
                filter_dict = {
                    'title': title,
                    'content': content,
                    'normalized_title': normalized_title,
                    'primary_theme_id': get_field(filter_result, 'primary_theme_id', None),
                    'primary_theme_name': get_field(filter_result, 'primary_theme_name', None),
                    'event_type': get_field(filter_result, 'event_type', ''),
                    'risk_flags': get_field(filter_result, 'risk_flags', []),
                }
                fixed_item = fix_war_drone_theme(filter_dict)
                for key, value in fixed_item.items():
                    if hasattr(filter_result, key):
                        setattr(filter_result, key, value)

                # 应用 ai_level
                level_dict = {
                    'title': title,
                    'content': content,
                    'normalized_title': normalized_title,
                    'event_type': get_field(filter_result, 'event_type', ''),
                    'final_score': get_field(filter_result, 'final_score', 0),
                    'related_stocks_count': get_field(filter_result, 'related_stocks_count', 0),
                    'primary_theme_id': get_field(filter_result, 'primary_theme_id', None),
                    'risk_flags': get_field(filter_result, 'risk_flags', []),
                    'trade_priority': get_field(filter_result, 'trade_priority', ''),
                }
                level_item = apply_ai_level(level_dict)
                for key, value in level_item.items():
                    if hasattr(filter_result, key):
                        setattr(filter_result, key, value)

                result.processing_status = "success"
                return result

            # 4. AI事件抽取
            try:
                ai_result = self.ai_extractor.extract(news, filter_result)

                # 记录AI原始输出
                result.ai_raw_output = get_field(ai_result, 'raw_ai_response', '')

                # 记录最终事件
                result.final_event = ai_result

                # 记录校验错误
                validation_errors = get_field(ai_result, 'validation_errors', [])
                result.validation_errors = validation_errors

                # 记录后处理注释
                postprocess_notes = get_field(ai_result, 'postprocess_notes', [])
                result.postprocess_notes = postprocess_notes

                # 判断是否使用fallback
                if validation_errors:
                    result.used_fallback = any('fallback' in str(e).lower() for e in validation_errors)

                # 5. 新增：标题公司名识别和付费内容检测
                try:
                    title = result.title
                    content = result.content or ''

                    # 5.1 提取标题中的公司名
                    candidates = self.title_extractor.extract(title)

                    # 5.2 解析公司名到股票代码
                    title_stocks = []
                    for candidate in candidates:
                        resolved = self.stock_resolver.resolve_company_name(candidate.name)
                        if resolved:
                            title_stocks.append({
                                'name': resolved['name'],
                                'code': resolved['code'],
                                'match_source': 'title_rule',
                                'match_confidence': resolved['match_confidence']
                            })

                    # 5.3 合并related_stocks
                    if title_stocks and ai_result:
                        ai_stocks = get_field(ai_result, 'related_stocks', [])
                        all_stocks_dict = {}

                        # 优先title识别的
                        for stock in title_stocks:
                            code = stock.get('code')
                            if code:
                                all_stocks_dict[code] = stock

                        # 再加AI的
                        for stock in ai_stocks:
                            code = get_field(stock, 'code', None)
                            if code and code not in all_stocks_dict:
                                all_stocks_dict[code] = {
                                    'name': get_field(stock, 'name', ''),
                                    'code': code,
                                    'match_source': 'ai_extraction',
                                    'match_confidence': 0.7
                                }

                        # 更新
                        if hasattr(ai_result, 'related_stocks'):
                            ai_result.related_stocks = list(all_stocks_dict.values())

                        # 清洗 related_stocks（过滤掉 AI、AIPPI 等非股票代码）
                        if hasattr(ai_result, 'related_stocks'):
                            original_count = len(ai_result.related_stocks)
                            ai_result.related_stocks = clean_related_stocks(ai_result.related_stocks)
                            cleaned_count = len(ai_result.related_stocks)

                            # 如果清洗掉了股票，添加标签
                            if original_count > cleaned_count:
                                if not hasattr(result, 'error_tags'):
                                    result.error_tags = []
                                if 'related_stocks_cleaned' not in result.error_tags:
                                    result.error_tags.append('related_stocks_cleaned')

                    # 5.4 付费内容检测
                    paid_result = self.paid_detector.detect(title, content)
                    result.paid_content_result = paid_result

                    # 5.5 付费标题限分
                    if paid_result.is_paid_locked and ai_result:
                        related_stocks = get_field(ai_result, 'related_stocks', [])
                        related_stocks_count = len(related_stocks) if related_stocks else 0

                        if paid_result.stock_visibility == "hidden_by_paid_content":
                            # 规则1: 隐藏股票
                            if hasattr(ai_result, 'event_type'):
                                ai_result.event_type = "research_teaser"
                            if hasattr(ai_result, 'related_stocks'):
                                ai_result.related_stocks = []
                            if hasattr(ai_result, 'final_score'):
                                ai_result.final_score = min(get_field(ai_result, 'final_score', 100), 60)
                            if hasattr(ai_result, 'trade_priority'):
                                ai_result.trade_priority = "watch"
                            if hasattr(ai_result, 'confidence'):
                                ai_result.confidence = min(get_field(ai_result, 'confidence', 1.0), 0.55)

                            if not hasattr(result, 'error_tags'):
                                result.error_tags = []
                            result.error_tags.extend(['paid_locked', 'stock_hidden_by_paid_content'])

                        elif related_stocks_count > 0:
                            # 规则2: 可见股票但付费
                            if hasattr(ai_result, 'final_score'):
                                ai_result.final_score = min(get_field(ai_result, 'final_score', 100), 65)
                            if hasattr(ai_result, 'trade_priority'):
                                priority = get_field(ai_result, 'trade_priority', 'watch')
                                if priority in ['high', 'urgent']:
                                    ai_result.trade_priority = 'candidate'

                            if not hasattr(result, 'error_tags'):
                                result.error_tags = []
                            result.error_tags.append('paid_locked')

                    # 5.6 高分无股票限分
                    if ai_result:
                        final_score = get_field(ai_result, 'final_score', 0)
                        related_stocks = get_field(ai_result, 'related_stocks', [])
                        event_type = get_field(ai_result, 'event_type', '')

                        exempted_types = ['macro_policy', 'major_policy', 'commodity_price_increase']

                        if final_score >= 70 and len(related_stocks) == 0 and event_type not in exempted_types:
                            if hasattr(ai_result, 'final_score'):
                                ai_result.final_score = min(final_score, 65)
                            if hasattr(ai_result, 'trade_priority'):
                                priority = get_field(ai_result, 'trade_priority', 'watch')
                                if priority in ['high', 'urgent']:
                                    ai_result.trade_priority = 'candidate'

                            if not hasattr(result, 'error_tags'):
                                result.error_tags = []
                            result.error_tags.append('score_capped_no_stock')

                except Exception as e:
                    # 标题识别失败不中断
                    if not hasattr(result, 'error_tags'):
                        result.error_tags = []
                    result.error_tags.append('title_extraction_failed')

                # === 新增：AI后处理 ===
                try:
                    if ai_result:
                        # 保护规则层提取的股票（不被AI删除）
                        if rule_stocks:
                            ai_stocks = get_field(ai_result, 'related_stocks', [])
                            # 合并规则股票和AI股票
                            merged_stocks_dict = {}
                            # 规则层股票优先
                            for stock in rule_stocks:
                                code = stock.get('code')
                                if code:
                                    merged_stocks_dict[code] = stock
                            # AI股票补充
                            for stock in ai_stocks:
                                code = get_field(stock, 'code', None)
                                if code and code not in merged_stocks_dict:
                                    merged_stocks_dict[code] = stock
                            # 更新
                            if hasattr(ai_result, 'related_stocks'):
                                ai_result.related_stocks = list(merged_stocks_dict.values())
                                ai_result.related_stocks_count = len(ai_result.related_stocks)

                        # 战争无人机修正
                        fix_item = {
                            'title': title,
                            'content': content,
                            'normalized_title': normalized_title,
                            'primary_theme_id': get_field(ai_result, 'primary_theme_id', None),
                            'primary_theme_name': get_field(ai_result, 'primary_theme_name', None),
                            'event_type': get_field(ai_result, 'event_type', ''),
                            'risk_flags': get_field(ai_result, 'risk_flags', []),
                        }
                        fixed_item = fix_war_drone_theme(fix_item)
                        for key, value in fixed_item.items():
                            if hasattr(ai_result, key):
                                setattr(ai_result, key, value)

                        # 应用 ai_level
                        level_item = {
                            'title': title,
                            'content': content,
                            'normalized_title': normalized_title,
                            'event_type': get_field(ai_result, 'event_type', ''),
                            'final_score': get_field(ai_result, 'final_score', 0),
                            'related_stocks_count': get_field(ai_result, 'related_stocks_count', 0),
                            'primary_theme_id': get_field(ai_result, 'primary_theme_id', None),
                            'risk_flags': get_field(ai_result, 'risk_flags', []),
                            'trade_priority': get_field(ai_result, 'trade_priority', ''),
                            'ai_level': get_field(ai_result, 'ai_level', None),
                        }
                        level_item = apply_ai_level(level_item)
                        for key, value in level_item.items():
                            if hasattr(ai_result, key):
                                setattr(ai_result, key, value)

                except Exception as e:
                    # 后处理失败不中断
                    if not hasattr(result, 'error_tags'):
                        result.error_tags = []
                    result.error_tags.append('post_processing_failed')

                result.processing_status = "success"

            except Exception as e:
                result.processing_status = "failed"
                result.processing_error = f"AI抽取失败: {str(e)}"
                result.ai_failed = True

        except Exception as e:
            result.processing_status = "failed"
            result.processing_error = f"处理失败: {str(e)}"

        return result


__all__ = ['SingleNewsPipeline']
