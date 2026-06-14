#!/usr/bin/env python3
"""
采集 SEC EDGAR Filings（升级版 - 公告事件引擎）

新功能：
- 8-K Item识别
- Exhibit附件下载
- SEC事件规则分类
- 完整打印格式
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fund_quant.data_sources.sec_edgar.filing_collector import FilingCollector
from fund_quant.data_sources.sec_edgar.filing_downloader import FilingDownloader
from fund_quant.data_sources.sec_edgar.exhibit_downloader import ExhibitDownloader
from fund_quant.data_sources.sec_edgar.sec_8k_item_parser import Sec8KItemParser
from fund_quant.data_sources.sec_edgar.content_merger import ContentMerger
from fund_quant.data_sources.sec_edgar.sec_event_rules import SECEventRules
from fund_quant.data_sources.sec_edgar.filing_normalizer import FilingNormalizer
from fund_quant.data_sources.sec_edgar.sec_config import DEFAULT_TICKERS

# 新增：AI模块导入
from fund_quant.nlp.event_extraction.sec_edgar import SEC8KEventExtractor
from fund_quant.nlp.scoring.sec_edgar import calculate_sec_event_score


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='采集SEC EDGAR Filings（升级版）',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--tickers', nargs='+', help='股票代码列表')
    parser.add_argument('--use-default-tickers', action='store_true', help='使用默认股票池')
    parser.add_argument('--forms', nargs='+', default=['8-K', '8-K/A'], help='表单类型')
    parser.add_argument('--days', type=int, default=7, help='最近N天')
    parser.add_argument('--since-date', type=str, help='起始日期 YYYY-MM-DD')
    parser.add_argument('--max-per-ticker', type=int, default=100, help='每个ticker最大filings数')

    # 新增参数
    parser.add_argument('--print-content', action='store_true', help='打印内容前3000字符')
    parser.add_argument('--skip-ai', action='store_true', help='跳过AI分析（仅采集和规则过滤）')
    parser.add_argument('--no-exhibits', action='store_true', help='不下载Exhibit附件')

    parser.add_argument('--save-json', action='store_true', help='保存JSON结果')
    parser.add_argument('--output-dir', type=str, default='output/sec_edgar', help='输出目录')

    return parser.parse_args()


def print_filing_detail(filing, items, classification, exhibits, ai_result, score_result, index):
    """打印filing详细信息"""
    print(f"\n{'='*80}")
    print(f"SEC Filing {index}")
    print(f"{'='*80}")
    print(f"Ticker: {filing.ticker}")
    print(f"Company: {filing.company_name}")
    print(f"Form: {filing.form_type}")
    print(f"Filing Date: {filing.filing_date}")
    print(f"Accession: {filing.accession_number}")

    if items:
        print(f"Items: {', '.join(items)}")

    print(f"Primary Document: {filing.primary_document}")

    if exhibits:
        exhibit_types = [e['type'] for e in exhibits if e.get('download_status') == 'success']
        print(f"Exhibits: {len(exhibit_types)} ({', '.join(exhibit_types)})")

    print(f"\nSEC规则过滤:")
    print(f"  action: {classification.get('action', 'unknown')}")
    print(f"  need_ai: {classification.get('need_ai', False)}")
    print(f"  pre_score: {classification.get('pre_score', 0)}")
    print(f"  event_hint: {classification.get('event_hint', '')}")
    print(f"  reason: {classification.get('reason', '')}")

    risk_flags = classification.get('risk_flags', [])
    if risk_flags:
        print(f"  risk_flags: {', '.join(risk_flags)}")

    # 打印AI结果
    if ai_result:
        # 先定义默认值，防止变量未定义
        ai_status = ai_result.get('ai_status', 'pending')
        fallback_used = ai_result.get('fallback_used', False)
        ai_error = ai_result.get('error', '')

        # 从ai_result中提取
        result = ai_result.get('ai_result', {}) or {}
        event_type = result.get('event_type', '')
        event_level = result.get('event_level', '')
        sentiment = result.get('sentiment', '')
        summary_zh = result.get('summary_zh', '')
        key_facts = result.get('key_facts', [])
        financial_metrics = result.get('financial_metrics', {})
        confidence = result.get('confidence', 0.0)

        print(f"\nAI抽取:")
        print(f"  status: {ai_status}")
        print(f"  fallback_used: {fallback_used}")

        if ai_error:
            print(f"  error: {ai_error}")

        if ai_status in ['success', 'partial_success'] and result:
            print(f"  event_type: {event_type}")
            print(f"  event_level: {event_level}")
            print(f"  sentiment: {sentiment}")

            if summary_zh:
                print(f"  summary_zh: {summary_zh[:100]}{'...' if len(summary_zh) > 100 else ''}")

            if key_facts:
                print(f"  key_facts: {len(key_facts)}条")
                for i, fact in enumerate(key_facts[:3], 1):
                    print(f"    {i}. {fact}")

            if financial_metrics and any(v != 'unknown' for v in financial_metrics.values()):
                print(f"  financial_metrics:")
                for k, v in financial_metrics.items():
                    if v != 'unknown':
                        print(f"    {k}: {v}")

            print(f"  confidence: {confidence:.2f}")

    # 打印评分
    if score_result:
        print(f"\n最终评分:")
        print(f"  final_score: {score_result.get('final_score', 0)}")
        print(f"  trade_priority: {score_result.get('trade_priority', 'D')}")
        print(f"  score_reason: {score_result.get('score_reason', '')}")


def save_results(results, args):
    """保存JSON结果"""
    if not args.save_json:
        return

    import json
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"sec_filings_{timestamp}.json"

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 结果已保存: {json_path}")


def print_summary(results):
    """打印汇总"""
    print(f"\n{'='*80}")
    print(f"汇总")
    print(f"{'='*80}")

    total = len(results)
    need_ai = sum(1 for r in results if r.get('classification', {}).get('need_ai'))

    from collections import Counter
    event_hints = Counter(r.get('classification', {}).get('event_hint', '') for r in results)

    print(f"总filings数: {total}")
    print(f"need_ai: {need_ai}")

    print(f"\nevent_hint分布:")
    for hint, count in event_hints.most_common():
        if hint:
            print(f"  {hint}: {count}")


def main():
    """主函数"""
    args = parse_args()

    # 确定tickers
    if args.use_default_tickers:
        tickers = DEFAULT_TICKERS
    elif args.tickers:
        tickers = [t.upper() for t in args.tickers]
    else:
        print("❌ 请指定 --tickers 或 --use-default-tickers")
        return 1

    print(f"\n{'='*80}")
    print(f"SEC EDGAR Filings 采集（升级版）")
    print(f"{'='*80}")
    print(f"Tickers: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}")
    print(f"Forms: {', '.join(args.forms)}")
    print(f"Days: {args.days if not args.since_date else f'Since {args.since_date}'}")
    print(f"No Exhibits: {args.no_exhibits}")
    print(f"{'='*80}\n")

    # 初始化
    collector = FilingCollector()
    downloader = FilingDownloader()
    exhibit_downloader = ExhibitDownloader()

    # 初始化AI抽取器（如果需要）
    ai_extractor = None
    if not args.skip_ai:
        try:
            ai_extractor = SEC8KEventExtractor()
            print("✅ AI抽取器初始化成功")
        except Exception as e:
            print(f"⚠️  AI抽取器初始化失败: {str(e)}")
            print("将跳过AI分析")
            args.skip_ai = True

    # 采集filings元数据
    print("📥 采集filings元数据...")
    filings = collector.collect_filings(
        tickers=tickers,
        forms=args.forms,
        since_date=args.since_date,
        days=args.days if not args.since_date else None,
        max_filings_per_ticker=args.max_per_ticker
    )

    if not filings:
        print("⚠️  未找到filings")
        return 0

    print(f"✅ 找到 {len(filings)} 个filings\n")

    # 处理每个filing
    results = []

    for i, filing in enumerate(filings, 1):
        try:
            # 1. 下载primary document
            primary_text = downloader.download_and_parse(filing.filing_url)

            if not primary_text:
                print(f"⚠️  Filing {i}: 下载失败")
                continue

            # 2. 提取Items
            items = Sec8KItemParser.extract_8k_items(primary_text)

            # 3. 下载exhibits
            exhibits = []
            if not args.no_exhibits:
                exhibits = exhibit_downloader.download_exhibits(
                    filing.cik,
                    filing.accession_number,
                    max_exhibits=5
                )

            # 4. 合并内容
            combined_text = ContentMerger.merge_primary_and_exhibits(
                primary_text,
                exhibits,
                max_chars=30000
            )

            # 5. SEC事件规则分类
            classification = SECEventRules.classify_sec_filing({
                'form_type': filing.form_type,
                'content': combined_text,
                'items': items,
                'download_status': 'success',
                'has_exhibits': len(exhibits) > 0
            })

            # 6. 标准化
            normalized = FilingNormalizer.normalize(
                filing=filing,
                content=combined_text,
                items=items,
                event_hint=classification['event_hint'],
                pre_score=classification['pre_score'],
                sec_rule_reason=classification['reason'],
                risk_flags=classification['risk_flags'],
                exhibits=exhibits
            )

            # 7. AI事件抽取（如果需要）
            ai_result = None
            if not args.skip_ai and classification.get('need_ai'):
                try:
                    print(f"  🤖 AI分析中...")
                    ai_result = ai_extractor.extract(normalized)
                except Exception as e:
                    print(f"  ⚠️  AI抽取失败: {str(e)}")
                    ai_result = {
                        'ai_status': 'failed',
                        'error': str(e),
                        'ai_result': None
                    }

            # 8. 评分
            score_result = calculate_sec_event_score(
                normalized,
                ai_result.get('ai_result') if ai_result else None
            )

            # 9. 打印
            print_filing_detail(filing, items, classification, exhibits, ai_result, score_result, i)

            # 打印内容
            if args.print_content:
                print(f"\nContent Preview (前3000字符):")
                print(f"{combined_text[:3000]}")
                print(f"...")

            # 保存结果
            results.append({
                **normalized,
                'classification': classification,
                'ai_status': ai_result.get('ai_status') if ai_result else 'skipped',
                'ai_result': ai_result.get('ai_result') if ai_result else None,
                'ai_error': ai_result.get('error') if ai_result else None,
                'fallback_used': ai_result.get('fallback_used', False) if ai_result else False,
                'final_score': score_result['final_score'],
                'trade_priority': score_result['trade_priority'],
                'score_reason': score_result['score_reason']
            })

        except Exception as e:
            print(f"❌ Filing {i} 处理失败: {str(e)}")
            continue

    # 保存JSON
    if args.save_json:
        save_results(results, args)

    # 打印汇总
    print_summary(results)

    print(f"\n✅ 采集完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
