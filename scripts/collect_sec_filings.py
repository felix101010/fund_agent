#!/usr/bin/env python3
"""
采集 SEC EDGAR Filings

遵守SEC Fair Access规则：
- 请求频率不超过10 req/s
- 默认2 req/s
- 必须设置User-Agent
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fund_quant.data_sources.sec_edgar.filing_collector import FilingCollector
from fund_quant.data_sources.sec_edgar.filing_downloader import FilingDownloader
from fund_quant.data_sources.sec_edgar.filing_normalizer import FilingNormalizer
from fund_quant.data_sources.sec_edgar.sec_config import DEFAULT_TICKERS


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='采集SEC EDGAR Filings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 采集NVDA最近7天的8-K
  python scripts/collect_sec_filings.py --tickers NVDA --forms 8-K --days 7

  # 采集多个ticker的8-K
  python scripts/collect_sec_filings.py --tickers NVDA TSLA AAPL --forms 8-K --days 30

  # 使用默认股票池
  python scripts/collect_sec_filings.py --use-default-tickers --forms 8-K --days 7
        """
    )

    parser.add_argument(
        '--tickers',
        nargs='+',
        help='股票代码列表（例如: NVDA TSLA AAPL）'
    )

    parser.add_argument(
        '--use-default-tickers',
        action='store_true',
        help='使用默认股票池'
    )

    parser.add_argument(
        '--forms',
        nargs='+',
        default=['8-K', '8-K/A'],
        help='表单类型（默认: 8-K 8-K/A）'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='最近N天（默认7）'
    )

    parser.add_argument(
        '--since-date',
        type=str,
        help='起始日期 YYYY-MM-DD（与--days二选一）'
    )

    parser.add_argument(
        '--max-per-ticker',
        type=int,
        default=100,
        help='每个ticker最大filings数（默认100）'
    )

    parser.add_argument(
        '--download',
        action='store_true',
        default=True,
        help='下载filing正文（默认开启）'
    )

    parser.add_argument(
        '--save-json',
        action='store_true',
        help='保存JSON结果'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/review/sec_filings',
        help='输出目录'
    )

    return parser.parse_args()


def print_filing(filing, index, content_len=None, error=None):
    """打印filing信息"""
    status = "✅" if not error else "❌"
    print(f"{status} [{index+1}] {filing.ticker} {filing.form_type} {filing.filing_date}")
    print(f"    CIK: {filing.cik}")
    print(f"    Accession: {filing.accession_number}")
    print(f"    Company: {filing.company_name}")

    if content_len:
        print(f"    Content: {content_len} chars")
    if error:
        print(f"    Error: {error}")

    print(f"    URL: {filing.filing_url[:80]}...")


def save_results(filings, contents, args):
    """保存结果"""
    if not args.save_json:
        return

    import json
    from pathlib import Path

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"sec_filings_{timestamp}.json"

    data = []
    for filing, content in zip(filings, contents):
        normalized = FilingNormalizer.normalize(filing, content or "")
        data.append(normalized)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 结果已保存: {json_path}")


def print_summary(filings, contents, download_errors):
    """打印汇总"""
    print(f"\n{'='*80}")
    print(f"汇总")
    print(f"{'='*80}")

    total = len(filings)
    downloaded = sum(1 for c in contents if c)
    failed = len(download_errors)

    print(f"总filings数: {total}")
    print(f"成功下载: {downloaded}")
    print(f"下载失败: {failed}")

    # 按ticker统计
    from collections import Counter
    ticker_count = Counter(f.ticker for f in filings)
    form_count = Counter(f.form_type for f in filings)

    print(f"\n按Ticker分布:")
    for ticker, count in ticker_count.most_common():
        print(f"  {ticker}: {count}")

    print(f"\n按表单类型分布:")
    for form, count in form_count.most_common():
        print(f"  {form}: {count}")


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
    print(f"SEC EDGAR Filings 采集")
    print(f"{'='*80}")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Forms: {', '.join(args.forms)}")
    print(f"Days: {args.days if not args.since_date else f'Since {args.since_date}'}")
    print(f"{'='*80}\n")

    # 初始化
    collector = FilingCollector()
    downloader = FilingDownloader()

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

    # 下载正文
    contents = []
    download_errors = []

    if args.download:
        print("📥 下载filing正文...")

        for i, filing in enumerate(filings):
            try:
                content = downloader.download_and_parse(filing.filing_url)
                contents.append(content)

                if content:
                    print_filing(filing, i, content_len=len(content))
                else:
                    print_filing(filing, i, error="下载失败或内容过短")
                    download_errors.append((filing, "下载失败"))

            except Exception as e:
                contents.append(None)
                print_filing(filing, i, error=str(e))
                download_errors.append((filing, str(e)))
    else:
        # 不下载，只打印元数据
        for i, filing in enumerate(filings):
            print_filing(filing, i)
            contents.append(None)

    # 保存结果
    if args.save_json:
        save_results(filings, contents, args)

    # 打印汇总
    print_summary(filings, contents, download_errors)

    print(f"\n✅ 采集完成")

    return 0


if __name__ == "__main__":
    sys.exit(main())
