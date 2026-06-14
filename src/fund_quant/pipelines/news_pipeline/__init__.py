"""
新闻处理流水线模块
"""
from fund_quant.pipelines.news_pipeline.pipeline_models import (
    NewsProcessResult,
    BatchProcessResult,
    DaemonRunResult
)
from fund_quant.pipelines.news_pipeline.single_news_pipeline import SingleNewsPipeline
from fund_quant.pipelines.news_pipeline.cls_batch_pipeline import ClsBatchPipeline
from fund_quant.pipelines.news_pipeline.pipeline_reporter import PipelineReporter

__all__ = [
    'NewsProcessResult',
    'BatchProcessResult',
    'DaemonRunResult',
    'SingleNewsPipeline',
    'ClsBatchPipeline',
    'PipelineReporter'
]
