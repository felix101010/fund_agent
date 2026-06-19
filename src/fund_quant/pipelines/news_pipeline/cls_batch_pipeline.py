"""
财联社批次处理流水线（历史专用版本）
单轮抓取 + 去重 + 处理 + 保存

注意：
- 这是历史遗留的财联社专用 pipeline
- 新新闻源建议使用 NewsBatchPipeline（news_batch_pipeline.py）
- 本文件暂时保留以兼容现有脚本
"""
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd

from fund_quant.data_sources.news.cls_api_collector import ClsApiCollector
from fund_quant.data_sources.news.deduplicator import NewsDeduplicator
from fund_quant.nlp.news_filter import NewsItem
from fund_quant.nlp.news_ai import AIEventExtractor, OllamaClient
from fund_quant.pipelines.news_pipeline.pipeline_models import BatchProcessResult, NewsProcessResult
from fund_quant.pipelines.news_pipeline.single_news_pipeline import SingleNewsPipeline
from fund_quant.pipelines.news_pipeline.pipeline_reporter import PipelineReporter
from fund_quant.data.storage.news_dedup_manager import NewsDedupManager
from fund_quant.research.news_review.error_classifier import ErrorClassifier
from collections import Counter


class ClsBatchPipeline:
    """
    财联社批次处理流水线

    职责：
    1. 调用 ClsApiCollector 抓取最新新闻
    2. 去重判断（新增/重复）
    3. 批量调用 SingleNewsPipeline 处理新增新闻
    4. 汇总 BatchProcessResult
    5. 保存 JSONL/CSV/summary
    """

    def __init__(
        self,
        limit: int = 20,
        only_new: bool = True,
        verbose: bool = False,
        model: Optional[str] = None,
        save_raw: bool = False,
        save_events: bool = False,
        save_jsonl: bool = True,
        save_csv: bool = True,
        save_summary: bool = True,
        output_dir: str = "data/review/cls_batch_outputs",
        seen_file_path: str = "data/review/seen_cls_news_ids.txt"
    ):
        """
        初始化

        Args:
            limit: 每轮抓取数量
            only_new: 只处理新增新闻
            verbose: 详细输出
            model: Ollama模型名称
            save_raw: 保存到raw_news表
            save_events: 保存到extracted_events表
            save_jsonl: 追加保存到单个JSONL文件
            save_csv: 追加保存到单个CSV文件（后续可导出）
            save_summary: 每轮单独生成summary（用于复盘）
            output_dir: 输出目录
            seen_file_path: 去重文件路径
        """
        self.limit = limit
        self.only_new = only_new
        self.verbose = verbose
        self.save_raw = save_raw
        self.save_events = save_events
        self.save_jsonl = save_jsonl
        self.save_csv = save_csv
        self.save_summary = save_summary
        self.output_dir = Path(output_dir)

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.collector = ClsApiCollector()
        self.dedup_manager = NewsDedupManager(seen_file_path=seen_file_path)

        # 初始化AI抽取器（如果指定了模型）
        if model:
            import os
            os.environ['OLLAMA_MODEL'] = model
            llm_client = OllamaClient()
            ai_extractor = AIEventExtractor(llm_client=llm_client)
        else:
            ai_extractor = AIEventExtractor()

        self.single_pipeline = SingleNewsPipeline(ai_extractor=ai_extractor)
        self.error_classifier = ErrorClassifier()
        self.reporter = PipelineReporter()

    def run_once(self, run_id: str, loop_index: int) -> BatchProcessResult:
        """
        执行一轮处理

        Args:
            run_id: 运行ID
            loop_index: 循环索引

        Returns:
            BatchProcessResult
        """
        # 生成batch_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"cls_{timestamp}_loop{loop_index:04d}"

        # 初始化结果
        batch_result = BatchProcessResult(
            batch_id=batch_id,
            run_id=run_id
        )

        try:
            # 1. 抓取新闻
            df = self.collector.fetch_latest(limit=self.limit)
            batch_result.total_fetched = len(df)

            if df.empty:
                return batch_result

            # 2. 去重
            df = NewsDeduplicator.remove_duplicates(df)

            # 3. 判断新增/重复
            new_news_list = []
            dup_news_list = []

            for _, row in df.iterrows():
                news_id = row.get('news_id', '')
                is_dup = self.dedup_manager.is_duplicate(news_id)

                if is_dup:
                    dup_news_list.append(row)
                else:
                    new_news_list.append(row)

            batch_result.new_count = len(new_news_list)
            batch_result.duplicated_count = len(dup_news_list)

            # 4. 保存原始新闻（可选）
            if self.save_raw and new_news_list:
                self._save_raw_news(new_news_list)

            # 5. 处理新增新闻
            if self.only_new:
                process_list = new_news_list
            else:
                process_list = list(df.iterrows())

            for row in process_list:
                if isinstance(row, tuple):
                    _, row = row

                # 转换为 NewsItem
                news_item = NewsItem(
                    news_id=row.get('news_id', ''),
                    source=row.get('source', 'cls'),
                    title=row.get('title', ''),
                    content=row.get('content', ''),
                    publish_time=row.get('publish_time', datetime.now())
                )

                # 处理单条新闻
                result = self.single_pipeline.process(
                    news=news_item,
                    batch_id=batch_id,
                    run_id=run_id,
                    is_new=True
                )

                # 添加错误标签
                result.error_tags = self.error_classifier.classify(result)

                # 标记为已seen
                self.dedup_manager.mark_as_seen(result.news_id)

                # 统计
                batch_result.processed_count += 1

                if result.processing_status == "success":
                    if result.need_ai:
                        batch_result.ai_success += 1
                        if result.used_fallback:
                            batch_result.fallback_count += 1
                elif result.processing_status == "failed":
                    batch_result.ai_failed += 1
                elif result.processing_status == "skipped":
                    batch_result.skipped_count += 1

                batch_result.results.append(result)

            # 6. 生成统计
            batch_result.stats = self._generate_stats(batch_result)

            # 7. 保存输出
            self._save_outputs(batch_result)

        except Exception as e:
            batch_result.stats['error'] = str(e)

        return batch_result

    def _save_raw_news(self, news_list):
        """保存原始新闻到 raw_news 表"""
        try:
            news_dicts = [row.to_dict() if hasattr(row, 'to_dict') else row for row in news_list]
            success, errors = self.dedup_manager.save_raw_news(news_dicts)
            if errors and self.verbose:
                print(f"⚠️  保存raw_news部分失败: {len(errors)}条")
        except Exception:
            pass  # 不中断流程

    def _generate_stats(self, batch_result: BatchProcessResult) -> dict:
        """生成统计信息"""
        stats = {}

        # 基础统计
        stats['total_fetched'] = batch_result.total_fetched
        stats['new_count'] = batch_result.new_count
        stats['duplicated_count'] = batch_result.duplicated_count
        stats['processed_count'] = batch_result.processed_count

        # AI统计
        stats['need_ai_count'] = sum(1 for r in batch_result.results if r.need_ai)
        stats['ai_success'] = batch_result.ai_success
        stats['ai_failed'] = batch_result.ai_failed
        stats['fallback_count'] = batch_result.fallback_count

        # 优先级分布
        priority_counter = Counter()
        theme_counter = Counter()
        error_tag_counter = Counter()

        for result in batch_result.results:
            if result.final_event:
                priority = getattr(result.final_event, 'trade_priority', 'watch')
                priority_counter[priority] += 1

                theme_name = getattr(result.final_event, 'primary_theme_name', '')
                if theme_name:
                    theme_counter[theme_name] += 1

            for tag in result.error_tags:
                error_tag_counter[tag] += 1

        stats['priority_distribution'] = dict(priority_counter)
        stats['theme_distribution'] = dict(theme_counter.most_common(10))
        stats['error_tags'] = dict(error_tag_counter.most_common(10))

        return stats

    def _save_outputs(self, batch_result: BatchProcessResult):
        """保存输出文件（追加模式）"""
        try:
            # 追加保存到单个JSONL文件
            if self.save_jsonl:
                jsonl_path = self.output_dir / "cls_news_all.jsonl"
                self.reporter.append_jsonl(batch_result, jsonl_path)

            # CSV不实时生成，等daemon结束后统一从JSONL导出
            # 这样避免每轮都重写CSV文件

            # 每轮单独生成summary（用于复盘单轮处理）
            if self.save_summary:
                summary_path = self.output_dir / f"{batch_result.batch_id}_summary.md"
                self.reporter.save_summary_md(batch_result, summary_path)

        except Exception as e:
            if self.verbose:
                print(f"⚠️  保存输出文件失败: {str(e)}")


__all__ = ['ClsBatchPipeline']
