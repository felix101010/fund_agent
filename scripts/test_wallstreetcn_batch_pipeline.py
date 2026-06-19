#!/usr/bin/env python3
"""
测试华尔街见闻批处理 Pipeline
使用通用 NewsBatchPipeline
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fund_quant.pipelines.news_pipeline.news_batch_pipeline import NewsBatchPipeline
from fund_quant.data_sources.news.wallstreetcn_collector import WallstreetcnCollector


def main():
    """测试华尔街见闻批处理"""

    print("=" * 80)
    print("华尔街见闻批处理 Pipeline 测试")
    print("=" * 80)
    print()

    # 1. 初始化采集器
    print("1. 初始化华尔街见闻采集器...")
    collector = WallstreetcnCollector()
    print("   ✓ 采集器初始化完成")
    print()

    # 2. 初始化批处理 Pipeline
    print("2. 初始化批处理 Pipeline...")
    pipeline = NewsBatchPipeline(
        source="wallstreetcn",
        source_role="market_context",
        collector=collector,
        limit=20,
        only_new=True,
        save_jsonl=True,
        save_by_source_jsonl=True,
        save_global_jsonl=True,
        save_summary=True,
        output_dir="data/review/news_batch_outputs",
    )
    print("   ✓ Pipeline 初始化完成")
    print()

    # 3. 运行一轮
    print("3. 运行一轮批处理...")
    print()

    run_id = f"test_wallstreetcn_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_result = pipeline.run_once(run_id=run_id, loop_index=1)

    # 4. 打印结果
    print()
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print(f"batch_id: {batch_result.batch_id}")
    print(f"run_id: {batch_result.run_id}")
    print()
    print(f"总抓取数: {batch_result.total_fetched}")
    print(f"新增新闻: {batch_result.new_count}")
    print(f"重复新闻: {batch_result.duplicated_count}")
    print(f"处理数量: {batch_result.processed_count}")
    print(f"跳过数量: {batch_result.skipped_count}")
    print()
    print(f"AI成功: {batch_result.ai_success}")
    print(f"AI失败: {batch_result.ai_failed}")
    print(f"fallback: {batch_result.fallback_count}")
    print()

    # 5. 输出文件
    output_dir = Path("data/review/news_batch_outputs")
    print("输出文件:")
    print(f"  按来源: {output_dir}/by_source/wallstreetcn_news_all.jsonl")
    print(f"  全局文件: {output_dir}/processed_news_all.jsonl")
    print(f"  摘要文件: {output_dir}/summaries/{batch_result.batch_id}_summary.md")
    print()

    # 6. 显示部分结果
    if batch_result.results:
        print("=" * 80)
        print("部分新闻示例")
        print("=" * 80)

        for i, result in enumerate(batch_result.results[:3], 1):
            print(f"\n新闻 {i}:")
            print(f"  来源: {result.source}")
            print(f"  角色: {result.source_role}")
            print(f"  标题: {result.title}")
            print(f"  时间: {result.publish_time}")
            print(f"  URL: {result.url}")
            print(f"  是否新增: {result.is_new}")
            print(f"  需要AI: {result.need_ai}")
            print(f"  处理状态: {result.processing_status}")

    print()
    print("=" * 80)
    print("✓ 测试完成")
    print("=" * 80)


if __name__ == '__main__':
    main()
