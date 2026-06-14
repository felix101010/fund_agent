"""
巨潮资讯批量处理流程
"""
from datetime import datetime
from typing import Optional
from fund_quant.data_sources.announcements import CninfoCollector, AnnouncementDeduplicator
from fund_quant.pipelines.announcement_pipeline.single_announcement_pipeline import SingleAnnouncementPipeline
from fund_quant.pipelines.announcement_pipeline.announcement_pipeline_models import (
    BatchAnnouncementResult,
    AnnouncementProcessResult
)
from fund_quant.pipelines.announcement_pipeline.announcement_reporter import AnnouncementReporter


class CninfoBatchPipeline:
    """
    巨潮资讯批量处理流程

    流程：
    1. 采集公告
    2. 去重
    3. 逐条处理
    4. 汇总结果
    5. 生成报告
    """

    def __init__(self):
        """初始化"""
        self.collector = CninfoCollector()
        self.deduplicator = AnnouncementDeduplicator()
        self.single_pipeline = SingleAnnouncementPipeline()
        self.reporter = AnnouncementReporter()

    def run(
        self,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        stock_code: Optional[str] = None,
        save_raw: bool = False,
        save_events: bool = False,
        save_jsonl: bool = True,
        save_csv: bool = True,
        output_dir: str = "output/cninfo"
    ) -> BatchAnnouncementResult:
        """
        运行批量处理

        Args:
            limit: 获取数量限制
            start_date: 开始日期
            end_date: 结束日期
            stock_code: 股票代码（可选）
            save_raw: 是否保存原始数据
            save_events: 是否保存事件数据
            save_jsonl: 是否保存JSONL
            save_csv: 是否保存CSV
            output_dir: 输出目录

        Returns:
            BatchAnnouncementResult
        """
        # 生成batch_id
        batch_id = f"cninfo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"📦 Batch ID: {batch_id}")

        # 1. 采集
        print(f"📡 开始采集公告...")
        if stock_code:
            raw_announcements = self.collector.fetch_by_stock(stock_code, start_date, end_date)
        elif start_date and end_date:
            raw_announcements = self.collector.fetch_by_date_range(start_date, end_date)
        else:
            raw_announcements = self.collector.fetch_latest(limit)

        total_fetched = len(raw_announcements)
        print(f"✅ 采集到 {total_fetched} 条公告")

        # 2. 去重
        print(f"🔍 去重...")
        deduplicated = self.deduplicator.deduplicate(raw_announcements)
        after_dedup = len(deduplicated)
        new_count = after_dedup
        print(f"✅ 去重后 {after_dedup} 条（新增 {new_count} 条）")

        # 3. 逐条处理
        print(f"⚙️  开始处理...")
        results = []
        processed_count = 0
        skipped_count = 0
        need_ai_count = 0
        need_pdf_count = 0

        for i, announcement in enumerate(deduplicated, 1):
            try:
                result = self.single_pipeline.process(announcement, batch_id)
                results.append(result)

                if result.processing_status == 'success':
                    processed_count += 1
                else:
                    skipped_count += 1

                if result.need_ai:
                    need_ai_count += 1
                if result.need_pdf:
                    need_pdf_count += 1

                if i % 10 == 0:
                    print(f"  处理进度: {i}/{after_dedup}")

            except Exception as e:
                print(f"❌ 处理失败: {announcement.announcement_id} - {e}")
                skipped_count += 1

        print(f"✅ 处理完成: 成功 {processed_count}，跳过 {skipped_count}")

        # 4. 汇总统计
        stats = self._calculate_stats(results)

        batch_result = BatchAnnouncementResult(
            batch_id=batch_id,
            total_fetched=total_fetched,
            after_dedup=after_dedup,
            new_count=new_count,
            processed_count=processed_count,
            skipped_count=skipped_count,
            need_ai_count=need_ai_count,
            need_pdf_count=need_pdf_count,
            results=results,
            stats=stats,
            created_at=datetime.now()
        )

        # 5. 生成报告
        print(f"📄 生成报告...")
        self.reporter.generate_reports(
            batch_result,
            output_dir=output_dir,
            save_jsonl=save_jsonl,
            save_csv=save_csv
        )

        print(f"🎉 批次 {batch_id} 处理完成！")
        return batch_result

    def _calculate_stats(self, results):
        """计算统计信息"""
        stats = {
            'action_distribution': {},
            'announcement_type_distribution': {},
            'priority_distribution': {}
        }

        for result in results:
            # action分布
            action = result.action
            stats['action_distribution'][action] = stats['action_distribution'].get(action, 0) + 1

            # 公告类型分布
            ann_type = result.announcement_type
            stats['announcement_type_distribution'][ann_type] = \
                stats['announcement_type_distribution'].get(ann_type, 0) + 1

            # 优先级分布
            if result.final_event:
                priority = result.final_event.get('trade_priority', 'unknown')
                stats['priority_distribution'][priority] = stats['priority_distribution'].get(priority, 0) + 1

        return stats


__all__ = ['CninfoBatchPipeline']
