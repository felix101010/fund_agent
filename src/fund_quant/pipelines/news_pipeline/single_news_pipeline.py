"""
单条新闻处理流水线
处理单条 NewsItem，不打印，只返回结果
"""
from typing import Any
from datetime import datetime

from fund_quant.nlp.news_filter import NewsItem, SimpleRuleFilter, UnknownDecisionFilter
from fund_quant.nlp.news_ai import AIEventExtractor
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
            # 1. 规则过滤
            filter_result = self.rule_filter.filter(news)
            result.filter_result = filter_result

            # 2. Unknown二次过滤
            action = get_field(filter_result, 'action', 'unknown')
            if action == "unknown":
                unknown_result = self.unknown_filter.refine(news, filter_result)
                result.unknown_refine_result = unknown_result
                filter_result = unknown_result

            # 3. 判断是否需要AI
            need_ai = get_field(filter_result, 'need_ai', False)
            result.need_ai = need_ai

            if not need_ai:
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
