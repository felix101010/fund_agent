"""
通用新闻批处理 Pipeline
支持任意新闻源的批量采集和处理
"""
from typing import Any, Optional, Iterator
from datetime import datetime
from pathlib import Path
import pandas as pd

from fund_quant.pipelines.news_pipeline.single_news_pipeline import SingleNewsPipeline
from fund_quant.pipelines.news_pipeline.pipeline_models import NewsProcessResult, BatchProcessResult
from fund_quant.pipelines.news_pipeline.pipeline_reporter import PipelineReporter
from fund_quant.data_sources.news.deduplicator import NewsDeduplicator
from fund_quant.data.storage.news_dedup_manager import NewsDedupManager
from fund_quant.nlp.news_filter import NewsItem
from fund_quant.common.logger import logger


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值（dict/Series/dataclass/object）"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    elif hasattr(obj, name):
        return getattr(obj, name, default)
    elif isinstance(obj, pd.Series):
        return obj.get(name, default)
    return default


class NewsBatchPipeline:
    """
    通用新闻批处理 Pipeline

    用于处理任意新闻源，替代 ClsBatchPipeline 的单源专用设计
    """

    def __init__(
        self,
        source: str,
        collector,
        source_role: str = "",
        limit: int = 20,
        only_new: bool = True,
        verbose: bool = False,
        model: Optional[str] = None,
        save_raw: bool = False,
        save_events: bool = False,
        save_jsonl: bool = True,
        save_by_source_jsonl: bool = True,
        save_global_jsonl: bool = True,
        save_summary: bool = True,
        output_dir: str = "data/review/news_batch_outputs",
        seen_file_path: Optional[str] = None
    ):
        """
        初始化通用批处理 Pipeline

        Args:
            source: 新闻源，例如 cls/wallstreetcn/jin10/reuters
            collector: 采集器实例
            source_role: 新闻源角色，例如 a_share_catalyst/market_context/macro_event
            limit: 每次抓取数量
            only_new: 是否只处理新增新闻
            verbose: 详细输出
            model: 指定AI模型
            save_raw: 是否保存原始新闻
            save_events: 是否保存结构化事件
            save_jsonl: 是否保存JSONL
            save_by_source_jsonl: 是否按来源保存
            save_global_jsonl: 是否保存到全局文件
            save_summary: 是否生成摘要
            output_dir: 输出目录
            seen_file_path: seen文件路径，默认 data/review/seen_{source}_news_ids.txt
        """
        self.source = source
        self.collector = collector
        self.source_role = source_role
        self.limit = limit
        self.only_new = only_new
        self.verbose = verbose
        self.save_raw = save_raw
        self.save_events = save_events
        self.save_jsonl = save_jsonl
        self.save_by_source_jsonl = save_by_source_jsonl
        self.save_global_jsonl = save_global_jsonl
        self.save_summary = save_summary
        self.output_dir = Path(output_dir)

        # 初始化子组件
        self.single_pipeline = SingleNewsPipeline()
        self.reporter = PipelineReporter()

        # 去重管理器
        if seen_file_path is None:
            seen_file_path = f"data/review/seen_{source}_news_ids.txt"
        self.dedup_manager = NewsDedupManager(seen_file_path)

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "by_source").mkdir(exist_ok=True)
        (self.output_dir / "summaries").mkdir(exist_ok=True)

        logger.info(f"{source} 批处理Pipeline初始化完成")
        if source_role:
            logger.info(f"  source_role: {source_role}")
        logger.info(f"  limit: {limit}")
        logger.info(f"  output_dir: {output_dir}")
        logger.info(f"  seen_file: {seen_file_path}")

    def run_once(self, run_id: str, loop_index: int) -> BatchProcessResult:
        """
        运行一轮批处理

        Args:
            run_id: 运行ID
            loop_index: 循环索引

        Returns:
            批次处理结果
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_id = f"{self.source}_{timestamp}_loop{loop_index:04d}"

        logger.info(f"\n{'='*80}")
        logger.info(f"批次: {batch_id}")
        logger.info(f"{'='*80}")

        # 初始化结果
        batch_result = BatchProcessResult(
            batch_id=batch_id,
            run_id=run_id
        )

        try:
            # 1. 采集新闻
            logger.info(f"1. 采集 {self.source} 新闻...")
            data = self.collector.fetch_latest(limit=self.limit)

            if data is None or (isinstance(data, (list, pd.DataFrame)) and len(data) == 0):
                logger.warning(f"{self.source} 采集失败或无数据")
                return batch_result

            # 统计抓取数量
            if isinstance(data, pd.DataFrame):
                batch_result.total_fetched = len(data)
            elif isinstance(data, list):
                batch_result.total_fetched = len(data)
            else:
                logger.warning(f"不支持的数据类型: {type(data)}")
                return batch_result

            logger.info(f"  抓取到 {batch_result.total_fetched} 条")

            # 2. 去重
            if isinstance(data, pd.DataFrame):
                logger.info("2. 去重...")
                data = NewsDeduplicator.remove_duplicates(data)

            # 3. 逐条处理
            logger.info("3. 逐条处理...")
            for item in self._iter_news_rows(data):
                try:
                    result = self._process_single_news(item, batch_id, run_id)
                    batch_result.results.append(result)

                    # 统计
                    if result.is_new:
                        batch_result.new_count += 1
                    else:
                        batch_result.duplicated_count += 1

                    if result.processing_status == "success":
                        batch_result.processed_count += 1
                        if result.need_ai:
                            batch_result.ai_success += 1
                        if result.used_fallback:
                            batch_result.fallback_count += 1
                    elif result.processing_status == "failed":
                        if result.ai_failed:
                            batch_result.ai_failed += 1
                    elif result.processing_status == "skipped":
                        batch_result.skipped_count += 1

                except Exception as e:
                    logger.error(f"  处理新闻失败: {e}")
                    continue

            # 4. 生成统计
            batch_result.stats = self._generate_stats(batch_result)

            # 5. 保存输出
            if self.save_jsonl:
                self._save_jsonl_outputs(batch_result)

            if self.save_summary:
                self._save_summary(batch_result)

            logger.info(f"\n{'='*80}")
            logger.info(f"批次汇总: {batch_id}")
            logger.info(f"{'='*80}")
            logger.info(f"抓取数量: {batch_result.total_fetched}")
            logger.info(f"新增新闻: {batch_result.new_count}")
            logger.info(f"重复新闻: {batch_result.duplicated_count}")
            logger.info(f"处理数量: {batch_result.processed_count}")
            logger.info(f"\nAI成功: {batch_result.ai_success}")
            logger.info(f"AI失败: {batch_result.ai_failed}")
            logger.info(f"fallback: {batch_result.fallback_count}")

            # wallstreetcn 专用统计
            if self.source == 'wallstreetcn':
                logger.info(f"\n{'='*80}")
                logger.info("WallStreetCN Summary:")
                logger.info(f"{'='*80}")

                # Context types
                context_types = batch_result.stats.get('context_types', {})
                if context_types:
                    logger.info("\nContext types:")
                    for ct, count in sorted(context_types.items(), key=lambda x: x[1], reverse=True):
                        logger.info(f"  {ct}: {count}")

                # AI levels
                ai_levels = batch_result.stats.get('ai_levels', {})
                if ai_levels:
                    logger.info("\nAI levels:")
                    for al, count in sorted(ai_levels.items(), key=lambda x: x[1], reverse=True):
                        logger.info(f"  {al}: {count}")

                # Market bias
                market_bias = batch_result.stats.get('market_bias', {})
                if market_bias:
                    logger.info("\nMarket bias:")
                    for mb, count in sorted(market_bias.items(), key=lambda x: x[1], reverse=True):
                        logger.info(f"  {mb}: {count}")

                # Top impact assets
                top_assets = batch_result.stats.get('top_impact_assets', {})
                if top_assets:
                    logger.info("\nTop impact assets:")
                    for asset, count in list(top_assets.items())[:10]:
                        logger.info(f"  {asset}: {count}")

            return batch_result

        except Exception as e:
            logger.error(f"批处理失败: {e}")
            import traceback
            traceback.print_exc()
            return batch_result

    def _iter_news_rows(self, data) -> Iterator[Any]:
        """
        迭代新闻行（兼容 DataFrame 和 List）

        Args:
            data: DataFrame 或 List[RawNews] 或 List[dict]

        Yields:
            单条新闻数据
        """
        if isinstance(data, pd.DataFrame):
            for _, row in data.iterrows():
                yield row
        elif isinstance(data, list):
            for item in data:
                yield item
        else:
            logger.warning(f"不支持的数据类型: {type(data)}")
            return

    def _process_single_news(self, item: Any, batch_id: str, run_id: str) -> NewsProcessResult:
        """
        处理单条新闻

        Args:
            item: 新闻数据（row/dict/RawNews）
            batch_id: 批次ID
            run_id: 运行ID

        Returns:
            处理结果
        """
        # 提取字段
        news_id = get_field(item, 'news_id', '')
        title = get_field(item, 'title', '')
        content = get_field(item, 'content', '')
        publish_time = get_field(item, 'publish_time', datetime.now())
        url = get_field(item, 'url', '')

        # 判断是否新增（is_duplicate 返回 True 表示重复，所以取反）
        is_new = not self.dedup_manager.is_duplicate(news_id)

        # wallstreetcn 特殊处理：生成 normalized_title 和市场上下文
        if self.source == 'wallstreetcn':
            from fund_quant.nlp.news_filter.keyword_rules import (
                build_normalized_title,
                classify_wallstreetcn_market_context,
            )

            # 生成 normalized_title
            normalized_title = build_normalized_title(title, content)

            # 分类市场上下文
            context_item = {
                'title': title,
                'content': content,
                'normalized_title': normalized_title,
            }
            market_context = classify_wallstreetcn_market_context(context_item)
        else:
            normalized_title = title
            market_context = {}

        # 创建 NewsItem（注意：NewsItem 不支持 url 字段）
        news = NewsItem(
            news_id=news_id,
            source=self.source,
            title=title,
            content=content,
            publish_time=publish_time
        )

        # 处理
        result = self.single_pipeline.process(news, batch_id, run_id, is_new)

        # 添加 source_role 和 url（在结果中保存）
        result.source_role = self.source_role
        result.url = url

        # wallstreetcn：强制注入市场上下文字段
        if self.source == 'wallstreetcn' and market_context:
            # 强制设置市场上下文字段
            for key, value in market_context.items():
                setattr(result, key, value)

            # 覆盖 need_ai（由 ai_level 决定）
            result.need_ai = market_context.get('ai_level') in ['light', 'urgent']

        # 标记为已seen
        if is_new:
            self.dedup_manager.mark_as_seen(news_id)

        return result

    def _generate_stats(self, batch_result: BatchProcessResult) -> dict:
        """生成统计信息"""
        stats = {
            "total_fetched": batch_result.total_fetched,
            "new_count": batch_result.new_count,
            "duplicated_count": batch_result.duplicated_count,
            "processed_count": batch_result.processed_count,
            "skipped_count": batch_result.skipped_count,
            "ai_success": batch_result.ai_success,
            "ai_failed": batch_result.ai_failed,
            "fallback_count": batch_result.fallback_count,
        }

        # 错误标签统计
        error_tags = {}
        for result in batch_result.results:
            for tag in result.error_tags:
                error_tags[tag] = error_tags.get(tag, 0) + 1
        stats["error_tags"] = error_tags

        # wallstreetcn 专用统计
        if self.source == 'wallstreetcn':
            context_types = {}
            ai_levels = {}
            market_bias = {}
            impact_assets_count = {}

            for result in batch_result.results:
                # context_type 统计
                ct = getattr(result, 'context_type', 'unknown')
                context_types[ct] = context_types.get(ct, 0) + 1

                # ai_level 统计
                al = getattr(result, 'ai_level', 'none')
                ai_levels[al] = ai_levels.get(al, 0) + 1

                # market_bias 统计
                mb = getattr(result, 'market_bias', 'neutral')
                market_bias[mb] = market_bias.get(mb, 0) + 1

                # impact_assets 统计
                assets = getattr(result, 'impact_assets', [])
                for asset in assets:
                    impact_assets_count[asset] = impact_assets_count.get(asset, 0) + 1

            stats['context_types'] = context_types
            stats['ai_levels'] = ai_levels
            stats['market_bias'] = market_bias
            stats['top_impact_assets'] = dict(sorted(impact_assets_count.items(), key=lambda x: x[1], reverse=True)[:10])

        return stats

    def _save_jsonl_outputs(self, batch_result: BatchProcessResult):
        """保存 JSONL 输出（只保存新增新闻，跳过重复）"""
        # 过滤出新增新闻
        new_results = [r for r in batch_result.results if r.is_new]

        if not new_results:
            logger.info("  没有新增新闻，跳过保存")
            return

        # 按来源保存
        if self.save_by_source_jsonl:
            source_file = self.output_dir / "by_source" / f"{self.source}_news_all.jsonl"
            self.reporter.append_results_to_jsonl(new_results, str(source_file))
            logger.info(f"  保存到: {source_file} ({len(new_results)} 条新增)")

        # 全局文件
        if self.save_global_jsonl:
            global_file = self.output_dir / "processed_news_all.jsonl"
            self.reporter.append_results_to_jsonl(new_results, str(global_file))
            logger.info(f"  保存到: {global_file} ({len(new_results)} 条新增)")

    def _save_summary(self, batch_result: BatchProcessResult):
        """保存摘要"""
        summary_file = self.output_dir / "summaries" / f"{batch_result.batch_id}_summary.md"
        self.reporter.save_batch_summary(batch_result, str(summary_file))
        logger.info(f"  摘要: {summary_file}")


__all__ = ['NewsBatchPipeline']
