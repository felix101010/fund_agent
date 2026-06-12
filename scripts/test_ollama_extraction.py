#!/usr/bin/env python3
"""
测试 Ollama + AI 事件抽取完整流程
"""
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from fund_quant.nlp.news_filter import NewsItem, SimpleRuleFilter
from fund_quant.nlp.news_ai import AIEventExtractor, OllamaClient

# 加载 .env 配置
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def test_ollama_extraction():
    """测试 Ollama AI 事件抽取"""

    # 测试新闻列表
    test_news_list = [
        {
            "news_id": "cls_001",
            "title": "生益科技：M10覆铜板已送样英伟达，等待验证结果",
            "content": "生益科技(600183.SH)在投资者互动平台表示，公司M10覆铜板已成功送样英伟达，目前正在等待客户验证结果。M10材料是适用于高速PCB的新型覆铜板材料。",
        },
        {
            "news_id": "cls_002",
            "title": "某公司澄清：暂无相关人形机器人业务",
            "content": "某公司今日发布澄清公告，称公司目前暂无相关人形机器人业务，此前市场传闻不实。",
        },
        {
            "news_id": "cls_003",
            "title": "专家表示：新能源板块长期向好",
            "content": "某专家在接受采访时表示，新能源板块未来有望受益于政策支持，长期向好。",
        },
        {
            "news_id": "cls_004",
            "title": "中兴通讯：800G光模块已实现量产",
            "content": "中兴通讯宣布，公司800G光模块产品已实现量产，并已向多个客户批量供货。",
        },
    ]

    # 1. 规则过滤
    print("=" * 80)
    print("步骤 1: 规则过滤")
    print("=" * 80)

    filter = SimpleRuleFilter()
    filter_results = []

    for news_data in test_news_list:
        news = NewsItem(
            news_id=news_data["news_id"],
            source="cls",
            title=news_data["title"],
            content=news_data["content"],
            publish_time=datetime.now()
        )

        filter_result = filter.filter(news)
        filter_results.append((news, filter_result))

        print(f"\n新闻: {news.title}")
        print(f"  过滤结果: {filter_result.action}")
        print(f"  需要AI: {filter_result.need_ai}")
        print(f"  预评分: {filter_result.pre_score}")
        if filter_result.matched_keywords:
            print(f"  匹配关键词: {filter_result.matched_keywords}")

    # 2. 初始化 Ollama 客户端
    print("\n" + "=" * 80)
    print("步骤 2: 初始化 Ollama 客户端")
    print("=" * 80)

    try:
        llm_client = OllamaClient()  # 自动从 .env 读取配置
        print("✅ Ollama 客户端初始化成功")
    except Exception as e:
        print(f"❌ Ollama 初始化失败: {e}")
        print("\n使用 Fallback 规则继续测试...")
        llm_client = None

    # 3. AI 事件抽取
    print("\n" + "=" * 80)
    print("步骤 3: AI 事件抽取")
    print("=" * 80)

    extractor = AIEventExtractor(llm_client=llm_client)

    for news, filter_result in filter_results:
        print(f"\n{'=' * 60}")
        print(f"新闻: {news.title}")
        print(f"{'=' * 60}")

        if not extractor.should_extract(filter_result):
            print("⏭️  跳过（不需要 AI 抽取）")
            continue

        try:
            print(f"\n🤖 AI 原始输出:")
            event_result = extractor.extract(news, filter_result)

            # 显示原始 AI 响应
            if event_result.raw_ai_response:
                print(f"  {event_result.raw_ai_response[:500]}")

            # 判断结果状态
            if not event_result.is_valid:
                print(f"\n❌ AI抽取无效，已拦截")
                print(f"  验证错误: {event_result.validation_errors}")
                if event_result.raw_ai_response:
                    print(f"\n  原始AI响应（前300字）:")
                    print(f"  {event_result.raw_ai_response[:300]}")
                continue

            # 检查是否使用了 fallback
            used_fallback = any("fallback" in err.lower() for err in event_result.validation_errors)

            if used_fallback:
                print(f"\n⚠️  AI输出无效，已使用 fallback 结果")
                if event_result.raw_ai_response:
                    print(f"\n  原始AI响应（前300字）:")
                    print(f"  {event_result.raw_ai_response[:300]}")
            else:
                print(f"\n✅ 抽取完成")

            print(f"  是否有效: {event_result.is_valid}")
            print(f"  市场相关: {event_result.is_market_relevant}")
            print(f"  事件类型: {event_result.event_type}")
            print(f"  主题: {', '.join(event_result.themes)}")
            print(f"  子题材: {event_result.sub_themes}")
            print(f"  情绪: {event_result.sentiment}")
            print(f"  事件级别: {event_result.event_level}")
            print(f"  新颖性: {event_result.novelty_type}")
            print(f"  置信度: {event_result.confidence:.2f}")

            if event_result.related_stocks:
                print(f"  关联股票:")
                for stock in event_result.related_stocks:
                    print(f"    - {stock.name} ({stock.code}): {stock.reason}")

            if event_result.risk_flags:
                print(f"  ⚠️  风险标记: {event_result.risk_flags}")

            if event_result.validation_errors:
                print(f"  ⚠️  验证信息: {event_result.validation_errors}")

            print(f"\n  摘要: {event_result.summary}")

        except Exception as e:
            print(f"❌ 抽取失败: {e}")

    # 4. 总结
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_ollama_extraction()
