#!/usr/bin/env python3
"""
测试真实财联社新闻 → 规则过滤 → AI 事件抽取完整流程
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fund_quant.data_sources.news.cls_api_collector import ClsApiCollector
from fund_quant.data_sources.news.deduplicator import NewsDeduplicator
from fund_quant.nlp.news_filter import NewsItem, FilterResult, SimpleRuleFilter, UnknownDecisionFilter
from fund_quant.nlp.news_ai import AIEventExtractor, OllamaClient

# 加载环境变量
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def safe_get(obj, key, default=None):
    """
    安全获取对象属性或字典值

    Args:
        obj: dict 或 dataclass/model 对象
        key: 字段名
        default: 默认值

    Returns:
        字段值或默认值
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='测试真实财联社新闻 AI 抽取流程',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=30,
        help='拉取新闻数量（默认30）'
    )

    parser.add_argument(
        '--only-ai',
        action='store_true',
        help='只显示需要 AI 分析的新闻'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细信息（AI 原始输出、后处理 corrections）'
    )

    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='指定 Ollama 模型（例如 qwen2.5:1.5b）'
    )

    parser.add_argument(
        '--save-raw',
        action='store_true',
        help='保存原始新闻到 raw_news 表'
    )

    parser.add_argument(
        '--save-events',
        action='store_true',
        help='保存抽取结果到 extracted_events 表'
    )

    return parser.parse_args()


def print_separator(char='=', length=80):
    """打印分隔线"""
    print(char * length)


def print_news_header(index, total, news_id, title, publish_time, url):
    """打印新闻头部"""
    print_separator()
    print(f"新闻 {index}/{total}")
    print_separator()
    print(f"标题: {title}")
    print(f"时间: {publish_time}")
    print(f"来源: cls")
    print(f"ID: {news_id}")
    if url:
        print(f"URL: {url}")
    print()


def print_filter_result(filter_result):
    """打印规则过滤结果"""
    print("规则过滤:")
    print(f"  action: {safe_get(filter_result, 'action', 'unknown')}")
    print(f"  need_ai: {safe_get(filter_result, 'need_ai', False)}")
    print(f"  pre_score: {safe_get(filter_result, 'pre_score', 0)}")

    matched_keywords = safe_get(filter_result, 'matched_keywords', [])
    if matched_keywords:
        print(f"  matched_keywords: {matched_keywords}")

    reasons = safe_get(filter_result, 'reasons', [])
    if reasons:
        print(f"  reason: {'; '.join(reasons)}")
    print()


def print_ai_result(event_result, verbose=False):
    """打印 AI 抽取结果"""
    print("AI抽取:")
    print(f"  event_type: {safe_get(event_result, 'event_type', 'unknown')}")
    print(f"  event_level: {safe_get(event_result, 'event_level', 'C')}")
    print(f"  sentiment: {safe_get(event_result, 'sentiment', 'neutral')}")

    # 优先使用 themes 属性（从 dataclass property），否则读 theme 字段
    if hasattr(event_result, 'themes'):
        themes = event_result.themes
        print(f"  themes(AI原始): {', '.join(themes) if themes else '无'}")
    else:
        theme = safe_get(event_result, 'theme', '')
        print(f"  themes(AI原始): {theme if theme else '无'}")

    # 新增：标准化主题
    primary_theme_name = safe_get(event_result, 'primary_theme_name', '')
    primary_theme_id = safe_get(event_result, 'primary_theme_id', '')
    if primary_theme_name:
        print(f"  primary_theme: {primary_theme_name} ({primary_theme_id})")

    sub_themes = safe_get(event_result, 'sub_themes', [])
    if sub_themes:
        print(f"  sub_themes: {', '.join(sub_themes)}")

    print(f"  novelty_type: {safe_get(event_result, 'novelty_type', 'unknown')}")
    print(f"  is_market_relevant: {safe_get(event_result, 'is_market_relevant', True)}")

    confidence = safe_get(event_result, 'confidence', 0.0)
    print(f"  confidence: {confidence:.2f}")

    # 新增：评分信息
    final_score = safe_get(event_result, 'final_score', 0.0)
    trade_priority = safe_get(event_result, 'trade_priority', 'watch')
    if final_score > 0:
        print(f"  final_score: {final_score:.1f}")
        print(f"  trade_priority: {trade_priority}")

    # 新增：风险标记
    risk_flags = safe_get(event_result, 'risk_flags', [])
    if risk_flags:
        print(f"  risk_flags: {', '.join(risk_flags)}")

    # 如果有 corrections（来自后处理器）
    if verbose:
        raw_response = safe_get(event_result, 'raw_ai_response', '')
        if raw_response:
            print(f"\n  AI原始输出（前300字）:")
            print(f"  {raw_response[:300]}")

    # postprocess_notes
    postprocess_notes = safe_get(event_result, 'postprocess_notes', [])
    if postprocess_notes and verbose:
        print(f"  postprocess_notes:")
        for note in postprocess_notes[:5]:  # 只显示前5条
            print(f"    - {note}")

    # 关联股票
    related_stocks = safe_get(event_result, 'related_stocks', [])
    if related_stocks:
        print(f"  related_stocks:")
        for stock in related_stocks:
            code = safe_get(stock, 'code', '')
            name = safe_get(stock, 'name', '')
            reason = safe_get(stock, 'reason', '')
            print(f"    - {name} {code}: {reason}")

    # 关联实体（非股票）
    related_entities = safe_get(event_result, 'related_entities', [])
    if related_entities:
        print(f"  related_entities:")
        for entity in related_entities:
            name = safe_get(entity, 'name', '')
            entity_type = safe_get(entity, 'entity_type', '')
            print(f"    - {name} ({entity_type})")

    # 新增：相关指数和ETF
    related_indices = safe_get(event_result, 'related_indices', [])
    related_etfs = safe_get(event_result, 'related_etfs', [])
    if related_indices:
        print(f"  related_indices: {', '.join(related_indices)}")
    if related_etfs:
        print(f"  related_etfs: {', '.join(related_etfs)}")

    # 新增：候选股票池主题
    candidate_stock_pool_theme = safe_get(event_result, 'candidate_stock_pool_theme', '')
    if candidate_stock_pool_theme:
        print(f"  candidate_stock_pool_theme: {candidate_stock_pool_theme}")

    print()


def print_validation_info(event_result, verbose=False):
    """打印验证信息"""
    is_valid = safe_get(event_result, 'is_valid', True)
    validation_errors = safe_get(event_result, 'validation_errors', [])

    print("验证:")
    print(f"  is_valid: {is_valid}")

    if validation_errors and verbose:
        print(f"  warnings: {validation_errors}")
    elif validation_errors:
        # 只显示关键错误
        critical = [e for e in validation_errors if '警告' not in e and 'code' not in e]
        if critical:
            print(f"  errors: {critical}")

    print()


def print_summary(event_result):
    """打印摘要"""
    summary = safe_get(event_result, 'summary', '')
    reason = safe_get(event_result, 'reason', '')

    text = summary or reason
    if text:
        print("摘要:")
        print(f"  {text}")
        print()


def main():
    """主函数"""
    args = parse_args()

    print_separator()
    print("真实财联社新闻 AI 抽取测试")
    print_separator()
    print(f"参数: limit={args.limit}, only_ai={args.only_ai}, verbose={args.verbose}")
    print(f"      save_raw={args.save_raw}, save_events={args.save_events}")
    if args.model:
        print(f"      model={args.model}")
    print()

    # 统计信息
    stats = {
        'total': 0,
        'after_dedup': 0,
        'need_ai': 0,
        'skipped': 0,
        'ai_success': 0,
        'ai_failed': 0,
        'fallback': 0,
        'actions': Counter(),
        'event_types': Counter(),
        'sentiments': Counter(),
        'themes': Counter(),
        'corrections': Counter()
    }

    # 1. 初始化采集器
    print("步骤 1: 初始化采集器")
    try:
        collector = ClsApiCollector()
        print("✅ ClsApiCollector 初始化成功")
    except Exception as e:
        print(f"❌ 初始化采集器失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 2. 初始化规则过滤器
    print("步骤 2: 初始化规则过滤器")
    try:
        rule_filter = SimpleRuleFilter()
        unknown_filter = UnknownDecisionFilter()
        print("✅ SimpleRuleFilter 初始化成功")
        print("✅ UnknownDecisionFilter 初始化成功")
    except Exception as e:
        print(f"❌ 初始化规则过滤器失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 3. 初始化 AI 抽取器
    print("步骤 3: 初始化 AI 抽取器")
    try:
        if args.model:
            import os
            os.environ['OLLAMA_MODEL'] = args.model

        llm_client = OllamaClient()
        extractor = AIEventExtractor(llm_client=llm_client)
        print(f"✅ AIEventExtractor 初始化成功")
    except Exception as e:
        print(f"❌ 初始化 AI 抽取器失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  将使用 fallback 规则抽取")
        extractor = AIEventExtractor(llm_client=None)

    print()

    # 4. 采集财联社新闻
    print_separator()
    print(f"步骤 4: 采集财联社新闻（limit={args.limit}）")
    print_separator()

    try:
        df = collector.fetch_latest(limit=args.limit)
    except Exception as e:
        print(f"❌ 采集失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    if df.empty:
        print("❌ 未采集到财联社新闻")
        return 1

    stats['total'] = len(df)
    print(f"✅ 采集到 {stats['total']} 条新闻\n")

    # 5. 去重
    print("步骤 5: 去重")
    df = NewsDeduplicator.remove_duplicates(df)
    stats['after_dedup'] = len(df)
    print(f"✅ 去重后 {stats['after_dedup']} 条新闻\n")

    # 6. 如果需要保存原始新闻
    if args.save_raw:
        print("步骤 6: 保存原始新闻到 raw_news")
        try:
            from fund_quant.data.storage.clickhouse_client import ClickHouseClient
            client = ClickHouseClient()
            records = df.to_dict('records')
            client.insert_many('raw_news', records)
            print(f"✅ 已保存 {len(records)} 条新闻到 raw_news\n")
        except Exception as e:
            print(f"❌ 保存失败: {e}\n")
            import traceback
            traceback.print_exc()

    # 7. 遍历新闻进行规则过滤和 AI 抽取
    print_separator()
    print("步骤 7: 规则过滤 + AI 抽取")
    print_separator()
    print()

    for idx, (_, row) in enumerate(df.iterrows(), 1):
        try:
            # 提取字段
            news_id = row.get('news_id', '')
            title = row.get('title', '')
            content = row.get('content', '')
            publish_time = row.get('publish_time', '')
            url = row.get('url', '')
            source = row.get('source', 'cls')

            # 构造 NewsItem
            news_item = NewsItem(
                news_id=news_id,
                source=source,
                title=title,
                content=content,
                publish_time=publish_time
            )

            # 规则过滤
            filter_result = rule_filter.filter(news_item)

            # Unknown 二次过滤
            original_action = safe_get(filter_result, 'action', 'unknown')
            original_need_ai = safe_get(filter_result, 'need_ai', False)

            if original_action == "unknown":
                filter_result = unknown_filter.refine(news_item, filter_result)
                refined_action = safe_get(filter_result, 'action', 'unknown')
                refined_need_ai = safe_get(filter_result, 'need_ai', False)

                # 如果发生了变化，记录
                if original_need_ai != refined_need_ai:
                    stats.setdefault('unknown_refined', 0)
                    stats['unknown_refined'] += 1

            action = safe_get(filter_result, 'action', 'unknown')
            need_ai = safe_get(filter_result, 'need_ai', False)

            stats['actions'][action] += 1

            # 如果只显示需要 AI 的新闻，跳过不需要的
            if args.only_ai and not need_ai:
                stats['skipped'] += 1
                continue

            # 打印新闻头部
            print_news_header(idx, stats['after_dedup'], news_id, title, publish_time, url)

            # 打印规则过滤结果
            print_filter_result(filter_result)

            # 如果不需要 AI，跳过
            if not need_ai:
                stats['skipped'] += 1
                continue

            stats['need_ai'] += 1

            # AI 抽取
            try:
                event_result = extractor.extract(news_item, filter_result)
                stats['ai_success'] += 1

                # 检查是否使用了 fallback
                validation_errors = safe_get(event_result, 'validation_errors', [])
                if any('fallback' in str(e).lower() for e in validation_errors):
                    stats['fallback'] += 1

                # 统计事件类型、情绪、主题
                event_type = safe_get(event_result, 'event_type', 'unknown')
                sentiment = safe_get(event_result, 'sentiment', 'neutral')
                is_market_relevant = safe_get(event_result, 'is_market_relevant', True)

                stats['event_types'][event_type] += 1
                stats['sentiments'][sentiment] += 1

                # 统计市场相关性
                if is_market_relevant:
                    stats.setdefault('market_relevant_count', 0)
                    stats['market_relevant_count'] += 1

                # 统计股票和实体数量
                related_stocks = safe_get(event_result, 'related_stocks', [])
                related_entities = safe_get(event_result, 'related_entities', [])

                stats.setdefault('related_stock_count', 0)
                stats['related_stock_count'] += len(related_stocks)

                stats.setdefault('related_entity_count', 0)
                stats['related_entity_count'] += len(related_entities)

                # 统计主题
                if hasattr(event_result, 'themes'):
                    themes = event_result.themes
                else:
                    theme = safe_get(event_result, 'theme', '')
                    themes = [t.strip() for t in theme.split(',') if t.strip()]

                for theme in themes:
                    if theme and theme != '无':
                        stats['themes'][theme] += 1

                # 新增：统计标准化主题
                primary_theme_name = safe_get(event_result, 'primary_theme_name', '')
                if primary_theme_name:
                    stats.setdefault('normalized_themes', Counter())
                    stats['normalized_themes'][primary_theme_name] += 1

                # 新增：统计交易优先级
                trade_priority = safe_get(event_result, 'trade_priority', 'watch')
                stats.setdefault('trade_priorities', Counter())
                stats['trade_priorities'][trade_priority] += 1

                # 新增：统计风险标记
                risk_flags = safe_get(event_result, 'risk_flags', [])
                if risk_flags:
                    stats.setdefault('risk_flags_count', 0)
                    stats['risk_flags_count'] += 1

                # 打印 AI 结果
                print_ai_result(event_result, verbose=args.verbose)

                # 打印验证信息
                print_validation_info(event_result, verbose=args.verbose)

                # 打印摘要
                print_summary(event_result)

            except Exception as e:
                print(f"❌ AI 抽取失败: {e}")
                import traceback
                traceback.print_exc()
                stats['ai_failed'] += 1
                print(f"AI抽取:\n  ❌ 抽取失败: {e}\n")

        except Exception as e:
            print(f"❌ 处理新闻 {idx} 失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 8. 如果需要保存事件
    if args.save_events:
        print_separator()
        print("步骤 8: 保存事件到 extracted_events")
        print("⚠️  TODO: 当前未实现 extracted_events 写入方法")
        print()

    # 9. 统计汇总
    print_separator()
    print("统计汇总")
    print_separator()
    print(f"拉取新闻数: {stats['total']}")
    print(f"去重后新闻数: {stats['after_dedup']}")
    print(f"unknown二次过滤修正数: {stats.get('unknown_refined', 0)}")
    print(f"need_ai: {stats['need_ai']}")
    print(f"skipped: {stats['skipped']}")
    print(f"AI成功: {stats['ai_success']}")
    print(f"AI失败: {stats['ai_failed']}")
    print(f"fallback: {stats['fallback']}")
    print(f"市场相关事件数: {stats.get('market_relevant_count', 0)}")
    print(f"关联股票总数: {stats.get('related_stock_count', 0)}")
    print(f"关联实体总数: {stats.get('related_entity_count', 0)}")
    print(f"有风险标记事件数: {stats.get('risk_flags_count', 0)}")
    print()

    if stats['actions']:
        print("规则 action 分布:")
        for action, count in stats['actions'].most_common():
            print(f"  {action}: {count}")
        print()

    if stats['event_types']:
        print("事件类型分布:")
        for event_type, count in stats['event_types'].most_common():
            print(f"  {event_type}: {count}")
        print()

    if stats['sentiments']:
        print("情绪分布:")
        for sentiment, count in stats['sentiments'].most_common():
            print(f"  {sentiment}: {count}")
        print()

    if stats['themes']:
        print("主题分布(AI原始):")
        for theme, count in stats['themes'].most_common(10):
            print(f"  {theme}: {count}")
        print()

    if stats.get('normalized_themes'):
        print("标准化主题分布:")
        for theme, count in stats['normalized_themes'].most_common(10):
            print(f"  {theme}: {count}")
        print()

    if stats.get('trade_priorities'):
        print("交易优先级分布:")
        for priority, count in stats['trade_priorities'].most_common():
            print(f"  {priority}: {count}")
        print()

    print_separator()
    print("✅ 测试完成")
    print_separator()

    return 0


if __name__ == "__main__":
    sys.exit(main())
