"""
Company IR新闻采集CLI（增强版 - 支持tier）
采集美股公司投资者关系网站的新闻
"""
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from fund_quant.data_sources.news.company_ir import (
    list_enabled_ir_tickers,
    get_ir_company_config,
    IRRSSCollector,
    IRPageCollector,
    IRDocumentDownloader,
    normalize_ir_item,
    IRRules,
    deduplicate_ir_items
)
from fund_quant.data_sources.news.company_ir.ir_company_config import (
    list_ir_tickers_by_tier,
    list_all_ir_tickers
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def should_fetch_article_auto(item: dict) -> bool:
    """
    判断是否应该自动抓取文章正文

    Args:
        item: 新闻item

    Returns:
        是否需要抓取
    """
    pre_score = item.get('pre_score', 0)
    event_hint = item.get('event_hint', '')

    # 高分直接抓取
    if pre_score >= 75:
        return True

    # 特定事件类型必须抓取
    high_value_events = [
        'earnings_release',
        'earnings_date_announcement',
        'executive_change',
        'strategic_partnership',
        'business_update',
        'ai_infrastructure',
        'product_launch',
        'product_ramp',
        'supply_chain_partnership',
        'capital_return',
    ]

    if event_hint in high_value_events:
        return True

    return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='采集Company IR新闻（支持tier分层）')

    parser.add_argument(
        '--tickers',
        nargs='+',
        default=None,
        help='股票代码列表，例如：NVDA TSLA AAPL MSFT'
    )
    parser.add_argument(
        '--tier',
        type=int,
        choices=[1, 2, 3],
        default=None,
        help='按tier采集：1=核心, 2=重点, 3=观察'
    )
    parser.add_argument(
        '--all-enabled',
        action='store_true',
        help='采集所有已启用的公司'
    )
    parser.add_argument(
        '--include-disabled',
        action='store_true',
        help='包含未启用的公司（需配合--tier使用）'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='采集最近N天的新闻（默认30天）'
    )
    parser.add_argument(
        '--save-json',
        action='store_true',
        help='保存为JSONL文件'
    )
    parser.add_argument(
        '--fetch-article',
        action='store_true',
        help='获取文章正文'
    )
    parser.add_argument(
        '--fetch-article-auto',
        action='store_true',
        help='自动抓取高价值新闻的正文（pre_score>=75或特定event_hint）'
    )
    parser.add_argument(
        '--use-page-fallback',
        action='store_true',
        default=True,
        help='当RSS采集失败时使用page fallback（默认启用）'
    )
    parser.add_argument(
        '--download-docs',
        action='store_true',
        help='下载文档附件'
    )

    args = parser.parse_args()

    # 确定要采集的tickers
    if args.tickers:
        tickers = [t.upper() for t in args.tickers]
    elif args.tier:
        tickers = list_ir_tickers_by_tier(args.tier, args.include_disabled)
        logger.info(f"Tier {args.tier}: {len(tickers)}家公司")
    elif args.all_enabled:
        tickers = list_enabled_ir_tickers()
    else:
        # 默认：只采集已启用的
        tickers = list_enabled_ir_tickers()

    logger.info(f"开始采集 {len(tickers)} 家公司的IR新闻")
    logger.info(f"Tickers: {', '.join(tickers)}")

    # 初始化组件
    rss_collector = IRRSSCollector()
    page_collector = IRPageCollector() if (args.fetch_article or args.fetch_article_auto) else None
    doc_downloader = IRDocumentDownloader() if args.download_docs else None
    rules = IRRules()

    all_items = []
    ticker_stats = {}  # 每个ticker的统计

    # 逐个采集
    for ticker in tickers:
        print(f"\n{'='*80}")
        print(f"采集 {ticker}")
        print(f"{'='*80}\n")

        # 初始化统计
        stats = {
            'raw_count': 0,
            'normalized_count': 0,
            'dedup_count': 0,
            'duplicate_removed': 0,
            'article_fetch_attempted': 0,
            'article_fetch_success': 0,
            'article_fetch_failed': 0,
            'article_fetch_skipped_low_score': 0,
        }

        # 获取配置
        config = get_ir_company_config(ticker)
        if not config:
            logger.warning(f"跳过 {ticker}: 未配置")
            continue

        # 检查enabled状态（除非使用--include-disabled）
        if not config.get('enabled', False) and not args.include_disabled:
            logger.warning(f"跳过 {ticker}: 未启用（使用 --include-disabled 来采集）")
            continue

        # 步骤1: RSS采集 raw items
        raw_items = rss_collector.collect(ticker, args.days)
        stats['raw_count'] = len(raw_items)
        logger.info(f"{ticker}: 采集到 {stats['raw_count']} 条RSS")

        # 步骤2: 标准化
        normalized_items = []
        for raw_item in raw_items:
            try:
                item = normalize_ir_item(ticker, config, raw_item, None)
                normalized_items.append(item)
            except Exception as e:
                logger.error(f"标准化失败: {e}")
                continue

        stats['normalized_count'] = len(normalized_items)

        # 步骤3: 去重（在分类和抓取之前）
        original_count = len(normalized_items)
        normalized_items = deduplicate_ir_items(normalized_items)
        stats['dedup_count'] = len(normalized_items)
        stats['duplicate_removed'] = original_count - stats['dedup_count']

        logger.info(f"{ticker}: 去重后 {stats['dedup_count']} 条（移除 {stats['duplicate_removed']} 条重复）")

        # 步骤4: 规则分类
        classified_items = []
        for item in normalized_items:
            try:
                item = rules.classify(item)
                classified_items.append(item)
            except Exception as e:
                logger.error(f"分类失败: {e}")
                continue

        # 步骤5: 高价值正文抓取（仅对去重后的items）
        for item in classified_items:
            try:
                # 判断是否需要抓取正文
                need_fetch = False
                if args.fetch_article:
                    need_fetch = True
                elif args.fetch_article_auto:
                    need_fetch = should_fetch_article_auto(item)

                if not need_fetch:
                    stats['article_fetch_skipped_low_score'] += 1
                    continue

                # 确保 page_collector 已初始化
                if not page_collector:
                    logger.warning("page_collector 未初始化，跳过正文抓取")
                    continue

                # 抓取正文
                link = item.get('link') or item.get('url')
                if link:
                    stats['article_fetch_attempted'] += 1

                    # 保存原始RSS content
                    rss_content = item.get('content', '') or item.get('summary', '') or ''
                    rss_content_len = len(rss_content)

                    if rss_content_len < 200:
                        article_detail = page_collector.fetch_article(link)

                        if article_detail:
                            article_content = article_detail.get('content', '')
                            article_content_len = len(article_content)

                            # 只有当抓取的正文更长时才使用
                            if article_content_len > rss_content_len:
                                item['content'] = article_content
                                item['article_content_len'] = article_content_len
                                item['article_fetch_status'] = 'success'
                                stats['article_fetch_success'] += 1
                                logger.info(f"✓ {ticker} | {item.get('title', '')[:40]} | {item.get('event_hint')} | RSS={rss_content_len} → Article={article_content_len}")
                            else:
                                # 保留RSS content，不覆盖为空
                                item['content'] = rss_content
                                item['article_content_len'] = article_content_len
                                item['article_fetch_status'] = 'failed_keep_rss_content'
                                stats['article_fetch_failed'] += 1
                                logger.warning(f"✗ {ticker} | {item.get('title', '')[:40]} | {item.get('event_hint')} | RSS={rss_content_len}, Article={article_content_len} (保留RSS)")

                            # 合并附件
                            if article_detail.get('attachments'):
                                item.setdefault('attachments', []).extend(article_detail['attachments'])
                        else:
                            # 保留RSS content
                            item['content'] = rss_content
                            item['article_fetch_status'] = 'failed_keep_rss_content'
                            stats['article_fetch_failed'] += 1
                    else:
                        item['article_fetch_status'] = 'not_needed'
                        logger.debug(f"跳过 {ticker} | {item.get('event_hint')} | RSS content 已足够 ({rss_content_len})")

                # 下载附件（可选）
                if args.download_docs and item.get('attachments'):
                    download_results = doc_downloader.download_attachments(
                        ticker,
                        item['publish_time'],
                        item['attachments']
                    )
                    item['download_results'] = download_results

            except Exception as e:
                logger.error(f"处理失败: {e}")
                stats['article_fetch_failed'] += 1
                continue

        # 添加到总列表
        all_items.extend(classified_items)
        ticker_stats[ticker] = stats

        # 打印当前ticker的items
        for item in classified_items:
            print_item_compact(item)

        # 打印ticker统计
        print(f"\n{ticker} 统计:")
        print(f"  Raw RSS: {stats['raw_count']}")
        print(f"  去重后: {stats['dedup_count']} (移除 {stats['duplicate_removed']} 条)")
        print(f"  正文抓取: {stats['article_fetch_attempted']} 次尝试, {stats['article_fetch_success']} 成功, {stats['article_fetch_failed']} 失败")


    # 最终统计
    print(f"\n{'='*80}")
    print(f"总体统计")
    print(f"{'='*80}")

    total_raw = sum(s['raw_count'] for s in ticker_stats.values())
    total_dedup = sum(s['dedup_count'] for s in ticker_stats.values())
    total_duplicate_removed = sum(s['duplicate_removed'] for s in ticker_stats.values())
    total_fetch_attempted = sum(s['article_fetch_attempted'] for s in ticker_stats.values())
    total_fetch_success = sum(s['article_fetch_success'] for s in ticker_stats.values())
    total_fetch_failed = sum(s['article_fetch_failed'] for s in ticker_stats.values())
    total_fetch_skipped = sum(s['article_fetch_skipped_low_score'] for s in ticker_stats.values())

    print(f"Raw RSS items: {total_raw}")
    print(f"Deduped items: {total_dedup}")
    print(f"Duplicate removed: {total_duplicate_removed}")
    print(f"Article fetch attempted: {total_fetch_attempted}")
    print(f"Article fetch success: {total_fetch_success}")
    print(f"Article fetch failed: {total_fetch_failed}")
    print(f"Article fetch skipped due to low score: {total_fetch_skipped}")

    # 按ticker详细统计
    if ticker_stats:
        print(f"\n{'='*80}")
        print(f"按Ticker统计")
        print(f"{'='*80}")
        print(f"{'Ticker':<8} | {'Raw':>5} | {'Dedup':>5} | {'NeedAI':>6} | {'HighVal':>7} | {'ArtOK':>5} | {'ArtFail':>7} | {'Empty':>5}")
        print("-" * 80)

        for ticker, stats in ticker_stats.items():
            # 计算每个ticker的需要AI和高价值数量
            ticker_items = [item for item in all_items if item.get('ticker') == ticker]
            need_ai_count = sum(1 for item in ticker_items if item.get('need_ai'))
            high_value_count = sum(1 for item in ticker_items if item.get('pre_score', 0) > 75)
            empty_content_count = sum(1 for item in ticker_items if len(item.get('content', '')) == 0)

            print(f"{ticker:<8} | {stats['raw_count']:>5} | {stats['dedup_count']:>5} | {need_ai_count:>6} | {high_value_count:>7} | {stats['article_fetch_success']:>5} | {stats['article_fetch_failed']:>7} | {empty_content_count:>5}")

    # 保存JSONL
    if args.save_json and all_items:
        output_dir = Path('output/company_ir')
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存全量
        output_file = output_dir / f'company_ir_{timestamp}_all.jsonl'
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in all_items:
                json.dump(item, f, ensure_ascii=False)
                f.write('\n')
        logger.info(f"保存全量到: {output_file}")

        # 保存AI队列（需要AI分析的）
        ai_queue_items = [item for item in all_items if item.get('need_ai')]
        if ai_queue_items:
            ai_queue_file = output_dir / f'company_ir_{timestamp}_ai_queue.jsonl'
            with open(ai_queue_file, 'w', encoding='utf-8') as f:
                for item in ai_queue_items:
                    json.dump(item, f, ensure_ascii=False)
                    f.write('\n')
            logger.info(f"保存AI队列到: {ai_queue_file} ({len(ai_queue_items)}条)")

    print(f"\n{'='*80}")
    print(f"采集完成")
    print(f"{'='*80}")
    print(f"总计: {len(all_items)} 条")
    print(f"需AI分析: {sum(1 for item in all_items if item.get('need_ai'))}")
    print(f"高价值(>75分): {sum(1 for item in all_items if item.get('pre_score', 0) > 75)}")
    print(f"总计: {len(all_items)} 条")
    print(f"需AI分析: {sum(1 for i in all_items if i.get('need_ai'))}")
    print(f"高价值(>75分): {sum(1 for i in all_items if i.get('pre_score', 0) > 75)}")


def print_item_compact(item: dict):
    """打印单条新闻（紧凑版）"""
    print(f"{'─'*80}")
    print(f"Title: {item.get('title', 'N/A')[:70]}")
    print(f"Event Hint: {item.get('event_hint', 'N/A')}")
    print(f"Pre Score: {item.get('pre_score', 0)} | Need AI: {item.get('need_ai', False)}")
    print(f"Content Len: {len(item.get('content', ''))}")
    print(f"URL: {item.get('url', 'N/A')[:70]}")
    print()


if __name__ == '__main__':
    main()
