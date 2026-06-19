#!/usr/bin/env python3
"""
测试华尔街见闻新闻采集器
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fund_quant.data_sources.news.wallstreetcn_collector import WallstreetcnCollector


def test_wallstreetcn_collector():
    """测试华尔街见闻采集器"""

    print("=" * 80)
    print("测试华尔街见闻新闻采集")
    print("=" * 80)
    print()

    # 创建采集器
    collector = WallstreetcnCollector()

    # 抓取新闻
    print("正在抓取最新 20 条新闻...\n")
    news_list = collector.fetch_latest(limit=20)

    if not news_list:
        print("❌ 采集失败")
        print("\n提示：请确认 RSSHub 正在运行")
        print("启动命令: docker run -d --name rsshub -p 1201:1200 diygod/rsshub")
        print("或访问: http://127.0.0.1:1201/wallstreetcn/live/global/1")
        return

    print(f"✓ 成功采集 {len(news_list)} 条新闻\n")
    print("=" * 80)

    # 显示新闻
    for idx, news in enumerate(news_list, 1):
        print(f"\n新闻 {idx}/{len(news_list)}")
        print("=" * 80)
        print(f"来源: {news.source}")
        print(f"角色: {news.source_role}")
        print(f"ID: {news.news_id}")
        print(f"标题: {news.title}")
        print(f"时间: {news.publish_time}")
        print(f"URL: {news.url}")

        # 显示正文摘要
        content = news.content
        if len(content) > 200:
            content = content[:200] + "..."
        print(f"正文摘要: {content}")
        print(f"采集延迟: {news.delay_seconds}秒")

    print("\n" + "=" * 80)
    print("✓ 测试完成")
    print("=" * 80)


def test_news_service():
    """测试 NewsService 集成"""
    from fund_quant.data_sources.news.news_service import NewsService

    print("\n" + "=" * 80)
    print("测试 NewsService 集成")
    print("=" * 80)
    print()

    service = NewsService()

    # 测试单独抓取华尔街见闻
    print("1. 测试单独抓取华尔街见闻...")
    wscn_df = service.fetch_latest("wallstreetcn", limit=10)
    if wscn_df is not None and not wscn_df.empty:
        print(f"✓ 成功抓取 {len(wscn_df)} 条")
    else:
        print("❌ 抓取失败")

    print()

    # 测试抓取所有来源
    print("2. 测试抓取所有来源...")
    all_df = service.fetch_all_latest(limit_per_source=5)
    if not all_df.empty:
        print(f"✓ 合并后总计 {len(all_df)} 条")
        print(f"  来源分布:")
        for source, count in all_df['source'].value_counts().items():
            print(f"    - {source}: {count} 条")
    else:
        print("❌ 抓取失败")

    print("\n" + "=" * 80)
    print("✓ 集成测试完成")
    print("=" * 80)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='测试华尔街见闻新闻采集')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    args = parser.parse_args()

    if args.integration:
        test_news_service()
    else:
        test_wallstreetcn_collector()
