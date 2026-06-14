"""
巨潮资讯批量采集脚本
"""
import argparse
from fund_quant.pipelines.announcement_pipeline import CninfoBatchPipeline


def main():
    parser = argparse.ArgumentParser(description='巨潮资讯批量公告采集')

    parser.add_argument('--limit', type=int, default=100, help='采集数量限制')
    parser.add_argument('--start-date', type=str, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--stock-code', type=str, help='股票代码（可选）')
    parser.add_argument('--save-raw', action='store_true', help='保存原始数据')
    parser.add_argument('--save-events', action='store_true', help='保存事件数据')
    parser.add_argument('--save-jsonl', action='store_true', default=True, help='保存JSONL（默认开启）')
    parser.add_argument('--save-csv', action='store_true', default=True, help='保存CSV（默认开启）')
    parser.add_argument('--output-dir', type=str, default='output/cninfo', help='输出目录')

    args = parser.parse_args()

    print("=" * 80)
    print("📢 巨潮资讯批量公告采集")
    print("=" * 80)

    # 运行pipeline
    pipeline = CninfoBatchPipeline()

    batch_result = pipeline.run(
        limit=args.limit,
        start_date=args.start_date,
        end_date=args.end_date,
        stock_code=args.stock_code,
        save_raw=args.save_raw,
        save_events=args.save_events,
        save_jsonl=args.save_jsonl,
        save_csv=args.save_csv,
        output_dir=args.output_dir
    )

    print("\n" + "=" * 80)
    print("✅ 批次处理完成")
    print("=" * 80)
    print(f"Batch ID: {batch_result.batch_id}")
    print(f"处理成功: {batch_result.processed_count}")
    print(f"需AI分析: {batch_result.need_ai_count}")
    print(f"需PDF解析: {batch_result.need_pdf_count}")


if __name__ == '__main__':
    main()
