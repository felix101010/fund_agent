#!/usr/bin/env python3
"""
测试免费Reuters新闻源可用性

法律说明：
- 本工具只读取公开聚合源的RSS标题/摘要
- 不访问Reuters付费API
- 不抓取Reuters付费正文
- 不绕过任何paywall
- 输出只用于个人技术测试和数据源可用性验证
- 如果未来要生产使用Reuters，应使用Reuters/LSEG正式授权API
"""
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fund_quant.data_sources.global_news.free_reuters_probe import FreeReutersProbe


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='测试免费Reuters新闻源可用性',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--query',
        type=str,
        help='单个查询词（例如 "Reuters NVIDIA"）'
    )

    parser.add_argument(
        '--default-queries',
        action='store_true',
        help='运行默认多个查询'
    )

    parser.add_argument(
        '--max-samples',
        type=int,
        default=10,
        help='每个查询的最大样本数（默认10）'
    )

    parser.add_argument(
        '--save-json',
        action='store_true',
        help='保存JSON结果'
    )

    parser.add_argument(
        '--save-csv',
        action='store_true',
        help='保存CSV结果'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/review/reuters_free_probe',
        help='输出目录'
    )

    return parser.parse_args()


def print_sample(item, index: int):
    """打印单个样本"""
    print(f"\n  [{index+1}] {item.title[:80]}")
    print(f"      source: {item.source}")
    print(f"      detected: {item.detected_source}")
    if item.publish_time:
        print(f"      time: {item.publish_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"      url: {item.url[:80]}")


def print_result(result):
    """打印探测结果"""
    print(f"\n{'='*80}")
    print(f"查询: {result.query}")
    print(f"{'='*80}")
    print(f"探测器: {result.probe_name}")
    print(f"是否可用: {result.is_available}")
    print(f"样本数: {result.sample_count}")

    if result.error_message:
        print(f"❌ 错误: {result.error_message}")
        return

    if result.sample_items:
        print(f"有标题: {result.has_title}")
        print(f"有摘要: {result.has_summary}")
        print(f"有时间: {result.has_publish_time}")
        print(f"有URL: {result.has_url}")
        print(f"有正文: {result.has_body}")

        reuters_count = result.get_reuters_count()
        print(f"\n✅ Reuters样本数: {reuters_count}/{result.sample_count}")
        print(f"推荐结论: {result.recommendation}")

        # 打印样本
        print(f"\n样本列表:")
        for i, item in enumerate(result.sample_items[:5]):  # 只显示前5条
            print_sample(item, i)

        if len(result.sample_items) > 5:
            print(f"\n  ... 还有 {len(result.sample_items) - 5} 条")


def save_results(results, args):
    """保存结果"""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存JSON
    if args.save_json:
        json_path = output_dir / f"reuters_probe_{timestamp}.json"
        json_data = []

        for result in results:
            result_dict = {
                'probe_name': result.probe_name,
                'query': result.query,
                'is_available': result.is_available,
                'sample_count': result.sample_count,
                'reuters_count': result.get_reuters_count(),
                'recommendation': result.recommendation,
                'error_message': result.error_message,
                'samples': []
            }

            for item in result.sample_items:
                result_dict['samples'].append({
                    'title': item.title,
                    'summary': item.summary,
                    'publish_time': item.publish_time.isoformat() if item.publish_time else None,
                    'url': item.url,
                    'source': item.source,
                    'detected_source': item.detected_source
                })

            json_data.append(result_dict)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 JSON已保存: {json_path}")

    # 保存CSV
    if args.save_csv:
        csv_path = output_dir / f"reuters_probe_{timestamp}.csv"
        rows = []

        for result in results:
            for item in result.sample_items:
                rows.append({
                    'probe_name': result.probe_name,
                    'query': result.query,
                    'title': item.title,
                    'summary': item.summary[:100] if item.summary else '',
                    'publish_time': item.publish_time.isoformat() if item.publish_time else '',
                    'url': item.url,
                    'source': item.source,
                    'detected_source': item.detected_source,
                    'has_body': item.has_body,
                    'recommendation': result.recommendation,
                    'legal_note': result.legal_note
                })

        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')

        print(f"💾 CSV已保存: {csv_path}")


def print_summary(results):
    """打印总结"""
    print(f"\n{'='*80}")
    print(f"总结")
    print(f"{'='*80}")

    total_queries = len(results)
    total_samples = sum(r.sample_count for r in results)
    total_reuters = sum(r.get_reuters_count() for r in results)

    available_results = [r for r in results if r.is_available]
    with_time = sum(1 for r in available_results if r.has_publish_time)
    with_url = sum(1 for r in available_results if r.has_url)

    print(f"总查询数: {total_queries}")
    print(f"总样本数: {total_samples}")
    print(f"Reuters样本数: {total_reuters}")

    if available_results:
        print(f"有发布时间的查询: {with_time}/{len(available_results)}")
        print(f"有URL的查询: {with_url}/{len(available_results)}")

    print(f"\n结论:")
    if total_reuters >= 5:
        print(f"✅ 可以用于标题级海外新闻实验")
        print(f"   - 免费聚合源可获取{total_reuters}条Reuters样本")
        print(f"   - 适合观察Reuters报道的海外事件")
        print(f"   - 仅限标题/摘要，无正文")
    elif total_samples > 0:
        print(f"⚠️  免费聚合源不稳定")
        print(f"   - 仅获取到{total_reuters}条Reuters样本")
        print(f"   - 不适合作为正式数据源")
    else:
        print(f"❌ 免费聚合源不可用")
        print(f"   - 无法获取样本")

    print(f"\n⚠️  重要提示:")
    print(f"   - 本工具仅用于技术验证")
    print(f"   - 不应作为正式生产Reuters数据源")
    print(f"   - 如需生产使用，请使用Reuters/LSEG官方授权API")


def main():
    """主函数"""
    args = parse_args()

    if not args.query and not args.default_queries:
        print("❌ 请指定 --query 或 --default-queries")
        return 1

    print(f"\n{'='*80}")
    print(f"免费Reuters新闻源可用性验证")
    print(f"{'='*80}")
    print(f"法律说明: 仅使用公开聚合源RSS标题/摘要，不访问付费API和正文")
    print(f"{'='*80}\n")

    # 初始化探测器
    probe = FreeReutersProbe()
    results = []

    try:
        # 单个查询
        if args.query:
            print(f"执行查询: {args.query}")
            result = probe.run_google_news_probe(args.query, args.max_samples)
            results.append(result)
            print_result(result)

        # 默认查询
        if args.default_queries:
            print(f"执行默认查询（共{len(probe.DEFAULT_QUERIES)}个）...")
            results = probe.run_all_default_queries(args.max_samples)

            for result in results:
                print_result(result)

        # 保存结果
        if args.save_json or args.save_csv:
            save_results(results, args)

        # 打印总结
        print_summary(results)

    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
