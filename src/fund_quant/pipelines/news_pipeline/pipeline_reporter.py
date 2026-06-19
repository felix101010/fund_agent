"""
Pipeline 报告生成器
打印和保存处理结果
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Any


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class PipelineReporter:
    """
    Pipeline 报告生成器

    职责：
    1. 打印单条新闻结果
    2. 打印批次汇总
    3. 保存 JSONL/CSV/summary.md
    """

    @staticmethod
    def print_news_result(result: Any, verbose: bool = False):
        """
        打印单条新闻处理结果

        Args:
            result: NewsProcessResult
            verbose: 是否详细输出
        """
        # wallstreetcn 专用打印格式
        if hasattr(result, 'source') and result.source == 'wallstreetcn':
            # 跳过重复新闻
            if hasattr(result, 'processing_status') and result.processing_status == 'skipped':
                print(f"[SKIP duplicate] {result.news_id} | {result.title[:50]}")
                return

            # 市场上下文格式
            print(f"\n{'─'*60}")
            print(f"Source: {result.source} | Role: {getattr(result, 'source_role', 'market_context')}")
            print(f"Title: {result.title}")

            if hasattr(result, 'context_type'):
                print(f"Context Type: {result.context_type}")

            if hasattr(result, 'impact_assets'):
                assets = ', '.join(result.impact_assets) if result.impact_assets else 'None'
                print(f"Impact Assets: {assets}")

            if hasattr(result, 'market_bias'):
                print(f"Market Bias: {result.market_bias}")

            if hasattr(result, 'importance'):
                print(f"Importance: {result.importance}")

            if hasattr(result, 'ai_level'):
                print(f"AI Level: {result.ai_level}")

            print(f"Need AI: {result.need_ai}")

            if hasattr(result, 'reason') and result.reason:
                print(f"Reason: {result.reason}")

            if hasattr(result, 'url') and result.url:
                print(f"URL: {result.url}")

            print(f"{'─'*60}")
            return

        # 原有打印逻辑（非 wallstreetcn）
        print(f"\n{'='*80}")
        print(f"新闻: {result.title[:60]}")
        print(f"news_id: {result.news_id}")
        print(f"处理状态: {result.processing_status}")

        if result.processing_status == "skipped":
            print(f"  跳过原因: {result.processing_error}")
            return

        if result.processing_status == "failed":
            print(f"  ❌ 失败: {result.processing_error}")
            return

        print(f"need_ai: {result.need_ai}")

        if result.final_event:
            event = result.final_event
            print(f"\n事件抽取结果:")
            print(f"  event_type: {get_field(event, 'event_type', 'unknown')}")
            print(f"  primary_theme: {get_field(event, 'primary_theme_name', '无')}")
            print(f"  trade_priority: {get_field(event, 'trade_priority', 'watch')}")
            print(f"  final_score: {get_field(event, 'final_score', 0):.1f}")

            risk_flags = get_field(event, 'risk_flags', [])
            if risk_flags:
                print(f"  risk_flags: {', '.join(risk_flags)}")

            related_stocks = get_field(event, 'related_stocks', [])
            if related_stocks:
                print(f"  related_stocks: {len(related_stocks)}只")

        if result.error_tags:
            print(f"error_tags: {', '.join(result.error_tags)}")

        if verbose and result.validation_errors:
            print(f"\nvalidation_errors:")
            for err in result.validation_errors[:3]:
                print(f"  - {err}")

    @staticmethod
    def print_batch_summary(batch_result: Any):
        """
        打印批次汇总

        Args:
            batch_result: BatchProcessResult
        """
        print(f"\n{'='*80}")
        print(f"批次汇总: {batch_result.batch_id}")
        print(f"{'='*80}")
        print(f"抓取数量: {batch_result.total_fetched}")
        print(f"新增新闻: {batch_result.new_count}")
        print(f"重复新闻: {batch_result.duplicated_count}")
        print(f"处理数量: {batch_result.processed_count}")
        print(f"")
        print(f"need_ai: {batch_result.stats.get('need_ai_count', 0)}")
        print(f"AI成功: {batch_result.ai_success}")
        print(f"AI失败: {batch_result.ai_failed}")
        print(f"fallback: {batch_result.fallback_count}")
        print(f"")

        # 优先级分布
        priority_dist = batch_result.stats.get('priority_distribution', {})
        if priority_dist:
            print(f"优先级分布:")
            for priority, count in sorted(priority_dist.items()):
                print(f"  {priority}: {count}")
            print(f"")

        # 主题分布
        theme_dist = batch_result.stats.get('theme_distribution', {})
        if theme_dist:
            print(f"主题分布(Top5):")
            for theme, count in list(theme_dist.items())[:5]:
                print(f"  {theme}: {count}")
            print(f"")

        # 错误标签
        error_tags = batch_result.stats.get('error_tags', {})
        if error_tags:
            print(f"错误标签(Top5):")
            for tag, count in list(error_tags.items())[:5]:
                print(f"  {tag}: {count}")

        print(f"{'='*80}\n")

    @staticmethod
    def print_daemon_loop_summary(daemon_run: Any):
        """
        打印 Daemon 单轮运行汇总

        Args:
            daemon_run: DaemonRunResult
        """
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ", end="")
        print(f"Loop {daemon_run.loop_index} - {daemon_run.status}")

        if daemon_run.batch_result:
            batch = daemon_run.batch_result
            print(f"  抓取:{batch.total_fetched} 新增:{batch.new_count} ", end="")
            print(f"AI:{batch.ai_success}/{batch.stats.get('need_ai_count', 0)} ", end="")
            print(f"fallback:{batch.fallback_count}")

        if daemon_run.error:
            print(f"  ❌ {daemon_run.error}")

    @staticmethod
    def append_results_to_jsonl(results: list, jsonl_path: str):
        """
        追加保存结果列表到 JSONL（支持多源，兼容 source_role 和 market_context）

        Args:
            results: List[NewsProcessResult]
            jsonl_path: JSONL文件路径
        """
        Path(jsonl_path).parent.mkdir(parents=True, exist_ok=True)

        # 追加模式
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            for result in results:
                record = {
                    'batch_id': result.batch_id,
                    'run_id': result.run_id,
                    'news_id': result.news_id,
                    'source': result.source,
                    'source_role': getattr(result, 'source_role', ''),
                    'title': result.title,
                    'content': result.content[:200] if result.content else '',
                    'publish_time': result.publish_time.isoformat() if result.publish_time else None,
                    'url': result.url,
                    'is_new': result.is_new,
                    'need_ai': result.need_ai,
                    'processing_status': result.processing_status,
                    'used_fallback': result.used_fallback,
                    'error_tags': result.error_tags,
                }

                # wallstreetcn 市场上下文字段
                if hasattr(result, 'context_type'):
                    record['context_type'] = getattr(result, 'context_type', '')
                if hasattr(result, 'impact_assets'):
                    record['impact_assets'] = getattr(result, 'impact_assets', [])
                if hasattr(result, 'market_bias'):
                    record['market_bias'] = getattr(result, 'market_bias', 'neutral')
                if hasattr(result, 'importance'):
                    record['importance'] = getattr(result, 'importance', 'low')
                if hasattr(result, 'ai_level'):
                    record['ai_level'] = getattr(result, 'ai_level', 'none')
                if hasattr(result, 'reason'):
                    record['reason'] = getattr(result, 'reason', '')
                if hasattr(result, 'theme_hint_ids'):
                    record['theme_hint_ids'] = getattr(result, 'theme_hint_ids', [])
                if hasattr(result, 'theme_hint_names'):
                    record['theme_hint_names'] = getattr(result, 'theme_hint_names', [])

                # 兼容 CLS 字段
                if result.final_event:
                    event = result.final_event
                    record['event_type'] = get_field(event, 'event_type', '')
                    record['primary_theme_id'] = get_field(event, 'primary_theme_id', '')
                    record['primary_theme_name'] = get_field(event, 'primary_theme_name', '')
                    record['trade_priority'] = get_field(event, 'trade_priority', '')
                    record['final_score'] = get_field(event, 'final_score', 0)
                    record['risk_flags'] = get_field(event, 'risk_flags', [])
                    record['confidence'] = get_field(event, 'confidence', 0)

                    # 股票和ETF
                    related_stocks = get_field(event, 'related_stocks', [])
                    record['related_stocks_count'] = len(related_stocks)
                    record['related_stocks'] = [
                        {'name': get_field(s, 'name', ''), 'code': get_field(s, 'code', '')}
                        for s in related_stocks
                    ]

                    related_etfs = get_field(event, 'related_etfs', [])
                    record['related_etfs'] = related_etfs

                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    @staticmethod
    def save_batch_summary(batch_result: Any, md_path: str):
        """
        保存批次摘要（wrapper方法）

        Args:
            batch_result: BatchProcessResult
            md_path: Markdown文件路径
        """
        PipelineReporter.save_summary_md(batch_result, Path(md_path))

    @staticmethod
    def append_jsonl(batch_result: Any, jsonl_path: Path):
        """
        追加保存 JSONL（单个文件，持续追加）

        Args:
            batch_result: BatchProcessResult
            jsonl_path: JSONL文件路径
        """
        # 追加模式
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            for result in batch_result.results:
                record = {
                    'batch_id': result.batch_id,
                    'run_id': result.run_id,
                    'news_id': result.news_id,
                    'source': result.source,
                    'title': result.title,
                    'content': result.content[:200],  # 截断
                    'publish_time': result.publish_time.isoformat() if result.publish_time else None,
                    'url': result.url,
                    'is_new': result.is_new,
                    'need_ai': result.need_ai,
                    'processing_status': result.processing_status,
                    'used_fallback': result.used_fallback,
                    'error_tags': result.error_tags,
                }

                if result.final_event:
                    event = result.final_event
                    record['event_type'] = get_field(event, 'event_type', '')
                    record['primary_theme_id'] = get_field(event, 'primary_theme_id', '')
                    record['primary_theme_name'] = get_field(event, 'primary_theme_name', '')
                    record['trade_priority'] = get_field(event, 'trade_priority', '')
                    record['final_score'] = get_field(event, 'final_score', 0)
                    record['risk_flags'] = get_field(event, 'risk_flags', [])
                    record['confidence'] = get_field(event, 'confidence', 0)

                    # 股票和ETF
                    related_stocks = get_field(event, 'related_stocks', [])
                    record['related_stocks_count'] = len(related_stocks)
                    record['related_stocks'] = [
                        {'name': get_field(s, 'name', ''), 'code': get_field(s, 'code', '')}
                        for s in related_stocks
                    ]

                    related_etfs = get_field(event, 'related_etfs', [])
                    record['related_etfs'] = related_etfs

                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    @staticmethod
    def save_summary_md(batch_result: Any, md_path: Path):
        """
        保存 summary.md（单轮独立）

        Args:
            batch_result: BatchProcessResult
            md_path: Markdown文件路径
        """
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 批次处理汇总\n\n")
            f.write(f"**batch_id**: {batch_result.batch_id}\n\n")
            f.write(f"**时间**: {batch_result.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"## 基础统计\n\n")
            f.write(f"- 抓取数量: {batch_result.total_fetched}\n")
            f.write(f"- 新增新闻: {batch_result.new_count}\n")
            f.write(f"- 重复新闻: {batch_result.duplicated_count}\n")
            f.write(f"- 处理数量: {batch_result.processed_count}\n")
            f.write(f"- need_ai: {batch_result.stats.get('need_ai_count', 0)}\n")
            f.write(f"- AI成功: {batch_result.ai_success}\n")
            f.write(f"- AI失败: {batch_result.ai_failed}\n")
            f.write(f"- fallback: {batch_result.fallback_count}\n\n")

            # 优先级分布
            f.write(f"## 优先级分布\n\n")
            priority_dist = batch_result.stats.get('priority_distribution', {})
            for priority in ['urgent', 'high', 'candidate', 'watch']:
                count = priority_dist.get(priority, 0)
                f.write(f"- {priority}: {count}\n")
            f.write(f"\n")

            # 主题分布
            f.write(f"## 主题分布\n\n")
            theme_dist = batch_result.stats.get('theme_distribution', {})
            for theme, count in theme_dist.items():
                f.write(f"- {theme}: {count}\n")
            f.write(f"\n")

            # 错误标签
            f.write(f"## 错误标签\n\n")
            error_tags = batch_result.stats.get('error_tags', {})
            for tag, count in error_tags.items():
                f.write(f"- {tag}: {count}\n")
            f.write(f"\n")

            # high/urgent新闻列表
            f.write(f"## High/Urgent 新闻\n\n")
            for result in batch_result.results:
                if result.final_event:
                    priority = get_field(result.final_event, 'trade_priority', '')
                    if priority in ['high', 'urgent']:
                        f.write(f"### [{priority.upper()}] {result.title}\n")
                        f.write(f"- news_id: {result.news_id}\n")
                        f.write(f"- 主题: {get_field(result.final_event, 'primary_theme_name', '')}\n")
                        f.write(f"- 评分: {get_field(result.final_event, 'final_score', 0):.1f}\n")
                        f.write(f"\n")


__all__ = ['PipelineReporter']
