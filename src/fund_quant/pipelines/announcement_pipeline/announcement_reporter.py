"""
公告报告生成器
生成CSV、JSONL和summary.md
"""
import json
import csv
from pathlib import Path
from typing import List
from fund_quant.pipelines.announcement_pipeline.announcement_pipeline_models import (
    BatchAnnouncementResult,
    AnnouncementProcessResult
)


class AnnouncementReporter:
    """
    公告报告生成器

    生成：
    1. JSONL文件
    2. CSV文件
    3. summary.md摘要
    """

    def generate_reports(
        self,
        batch_result: BatchAnnouncementResult,
        output_dir: str = "output/cninfo",
        save_jsonl: bool = True,
        save_csv: bool = True
    ):
        """
        生成报告

        Args:
            batch_result: 批次结果
            output_dir: 输出目录
            save_jsonl: 是否保存JSONL
            save_csv: 是否保存CSV
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        batch_id = batch_result.batch_id

        # 1. JSONL
        if save_jsonl:
            jsonl_path = output_path / f"{batch_id}.jsonl"
            self._save_jsonl(batch_result.results, jsonl_path)
            print(f"  ✅ JSONL: {jsonl_path}")

        # 2. CSV
        if save_csv:
            csv_path = output_path / f"{batch_id}.csv"
            self._save_csv(batch_result.results, csv_path)
            print(f"  ✅ CSV: {csv_path}")

        # 3. Summary
        summary_path = output_path / f"{batch_id}_summary.md"
        self._save_summary(batch_result, summary_path)
        print(f"  ✅ Summary: {summary_path}")

    def _save_jsonl(self, results: List[AnnouncementProcessResult], path: Path):
        """保存JSONL"""
        with open(path, 'w', encoding='utf-8') as f:
            for result in results:
                json.dump(result.to_dict(), f, ensure_ascii=False)
                f.write('\n')

    def _save_csv(self, results: List[AnnouncementProcessResult], path: Path):
        """保存CSV"""
        if not results:
            return

        # CSV字段（阶段2增强）
        fieldnames = [
            'batch_id', 'announcement_id', 'stock_code', 'stock_name',
            'title', 'publish_time', 'announcement_type_raw', 'announcement_type',
            'action', 'need_ai', 'need_pdf', 'pre_score',
            'matched_keywords', 'event_type', 'primary_theme_id', 'primary_theme_name',
            'secondary_theme_id', 'secondary_theme_name',
            'trade_priority', 'final_score', 'risk_flags',
            'signal_direction', 'risk_priority',
            'pdf_parsed', 'pdf_unparsed_score_cap',
            'pdf_download_status', 'pdf_parse_status', 'pdf_text_length', 'pdf_extraction_method',
            'related_stocks_count', 'validation_errors', 'postprocess_notes',
            'error_tags', 'processing_status'
        ]

        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in results:
                final_event = result.final_event or {}

                row = {
                    'batch_id': result.batch_id,
                    'announcement_id': result.announcement_id,
                    'stock_code': result.stock_code,
                    'stock_name': result.stock_name,
                    'title': result.title,
                    'publish_time': result.publish_time.isoformat() if result.publish_time else '',
                    'announcement_type_raw': result.announcement_type_raw,
                    'announcement_type': result.announcement_type,
                    'action': result.action,
                    'need_ai': result.need_ai,
                    'need_pdf': result.need_pdf,
                    'pre_score': result.pre_score,
                    'matched_keywords': ','.join(result.matched_keywords),
                    'event_type': final_event.get('event_type', ''),
                    'primary_theme_id': final_event.get('primary_theme_id', ''),
                    'primary_theme_name': final_event.get('primary_theme_name', ''),
                    'secondary_theme_id': final_event.get('secondary_theme_id', ''),
                    'secondary_theme_name': final_event.get('secondary_theme_name', ''),
                    'trade_priority': final_event.get('trade_priority', ''),
                    'final_score': final_event.get('final_score', ''),
                    'risk_flags': ','.join(final_event.get('risk_flags', [])),
                    'signal_direction': final_event.get('signal_direction', ''),
                    'risk_priority': final_event.get('risk_priority', ''),
                    'pdf_parsed': result.pdf_parsed,
                    'pdf_unparsed_score_cap': result.pdf_unparsed_score_cap or '',
                    'pdf_download_status': result.pdf_download_status,
                    'pdf_parse_status': result.pdf_parse_status,
                    'pdf_text_length': result.pdf_text_length,
                    'pdf_extraction_method': result.pdf_extraction_method,
                    'related_stocks_count': len(final_event.get('related_stocks', [])),
                    'validation_errors': ','.join(result.validation_errors),
                    'postprocess_notes': ','.join(result.postprocess_notes),
                    'error_tags': ','.join(result.error_tags),
                    'processing_status': result.processing_status
                }
                writer.writerow(row)

    def _save_summary(self, batch_result: BatchAnnouncementResult, path: Path):
        """保存摘要（阶段2增强）"""
        lines = []
        lines.append(f"# 巨潮资讯批次处理报告\n")
        lines.append(f"**Batch ID**: {batch_result.batch_id}\n")
        lines.append(f"**处理时间**: {batch_result.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"\n## 统计摘要\n")
        lines.append(f"- 总采集数: {batch_result.total_fetched}")
        lines.append(f"- 去重后: {batch_result.after_dedup}")
        lines.append(f"- 新增: {batch_result.new_count}")
        lines.append(f"- 处理成功: {batch_result.processed_count}")
        lines.append(f"- 跳过: {batch_result.skipped_count}")
        lines.append(f"- 需AI分析: {batch_result.need_ai_count}")
        lines.append(f"- 需PDF解析: {batch_result.need_pdf_count}\n")

        # action分布
        lines.append(f"\n## Action分布\n")
        for action, count in batch_result.stats.get('action_distribution', {}).items():
            pct = count / batch_result.processed_count * 100 if batch_result.processed_count else 0
            lines.append(f"- {action}: {count} ({pct:.1f}%)")

        # 公告类型分布
        lines.append(f"\n## 公告类型分布（Top 10）\n")
        type_dist = batch_result.stats.get('announcement_type_distribution', {})
        sorted_types = sorted(type_dist.items(), key=lambda x: x[1], reverse=True)[:10]
        for ann_type, count in sorted_types:
            lines.append(f"- {ann_type}: {count}")

        # 优先级分布
        lines.append(f"\n## 优先级分布\n")
        for priority, count in batch_result.stats.get('priority_distribution', {}).items():
            lines.append(f"- {priority}: {count}")

        # 阶段2新增：risk_priority分布
        risk_priority_dist = {}
        signal_direction_dist = {}
        pdf_status_dist = {}
        pdf_parsed_count = 0
        score_capped_count = 0
        missing_theme_count = 0

        for result in batch_result.results:
            if result.final_event:
                # risk_priority
                rp = result.final_event.get('risk_priority', 'none')
                risk_priority_dist[rp] = risk_priority_dist.get(rp, 0) + 1

                # signal_direction
                sd = result.final_event.get('signal_direction', 'neutral')
                signal_direction_dist[sd] = signal_direction_dist.get(sd, 0) + 1

                # 缺失主题
                if result.action in ['analyze', 'risk_review'] and not result.final_event.get('primary_theme_id'):
                    missing_theme_count += 1

            # PDF状态
            if result.pdf_download_status != 'not_required':
                pdf_status_dist[result.pdf_download_status] = pdf_status_dist.get(result.pdf_download_status, 0) + 1

            if result.pdf_parsed:
                pdf_parsed_count += 1

            if result.pdf_unparsed_score_cap:
                score_capped_count += 1

        lines.append(f"\n## 风险优先级分布（risk_priority）\n")
        for rp, count in sorted(risk_priority_dist.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {rp}: {count}")

        lines.append(f"\n## 信号方向分布（signal_direction）\n")
        for sd, count in sorted(signal_direction_dist.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {sd}: {count}")

        lines.append(f"\n## PDF处理统计\n")
        lines.append(f"- PDF下载尝试: {sum(pdf_status_dist.values())}")
        for status, count in pdf_status_dist.items():
            lines.append(f"  - {status}: {count}")
        lines.append(f"- PDF解析成功: {pdf_parsed_count}")
        lines.append(f"- 标题级限分数: {score_capped_count}")

        # 高价值公告
        lines.append(f"\n## 高价值公告（urgent/high）\n")
        high_value = [r for r in batch_result.results
                      if r.final_event and r.final_event.get('trade_priority') in ['urgent', 'high']]
        for result in high_value[:20]:
            theme = f"[{result.final_event.get('primary_theme_id', 'N/A')}]" if result.final_event else ""
            lines.append(f"- [{result.stock_code}] {result.stock_name} {theme}")
            lines.append(f"  {result.title[:80]}")

        # 风险紧急公告
        lines.append(f"\n## 风险紧急公告（risk_priority=urgent）\n")
        urgent_risks = [r for r in batch_result.results
                        if r.final_event and r.final_event.get('risk_priority') == 'urgent']
        if urgent_risks:
            for result in urgent_risks:
                lines.append(f"- [{result.stock_code}] {result.stock_name}")
                lines.append(f"  {result.title}")
                lines.append(f"  风险: {', '.join(result.final_event.get('risk_flags', []))}")
        else:
            lines.append("- 无")

        # 待优化案例
        lines.append(f"\n## 待优化案例\n")
        if missing_theme_count > 0:
            lines.append(f"### 缺失主题映射（analyze/risk_review但无primary_theme_id）: {missing_theme_count}条\n")
            for result in [r for r in batch_result.results
                          if r.action in ['analyze', 'risk_review']
                          and r.final_event
                          and not r.final_event.get('primary_theme_id')][:5]:
                lines.append(f"- [{result.stock_code}] {result.stock_name}: {result.title[:60]}")

        pdf_failed = [r for r in batch_result.results if r.pdf_download_status == 'failed']
        if pdf_failed:
            lines.append(f"\n### PDF下载失败: {len(pdf_failed)}条\n")
            for result in pdf_failed[:5]:
                lines.append(f"- {result.announcement_id}: {result.title[:60]}")

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


__all__ = ['AnnouncementReporter']
