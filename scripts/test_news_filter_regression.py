#!/usr/bin/env python3
"""
新闻过滤器回归测试
测试 related_stocks 清洗、题材识别、事件类型识别
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fund_quant.nlp.news_filter import NewsItem
from fund_quant.pipelines.news_pipeline.single_news_pipeline import SingleNewsPipeline


def print_result(title: str, result):
    """打印测试结果"""
    print(f"\n{'='*80}")
    print(f"标题: {title}")
    print(f"{'='*80}")
    print(f"need_ai: {result.need_ai}")

    if result.final_event:
        event = result.final_event
        print(f"event_type: {getattr(event, 'event_type', 'N/A')}")
        print(f"primary_theme_name: {getattr(event, 'primary_theme_name', 'N/A')}")
        print(f"final_score: {getattr(event, 'final_score', 0)}")
        print(f"trade_priority: {getattr(event, 'trade_priority', 'N/A')}")

        related_stocks = getattr(event, 'related_stocks', [])
        print(f"related_stocks ({len(related_stocks)}):")
        for stock in related_stocks[:5]:
            code = stock.get('code', 'N/A') if isinstance(stock, dict) else getattr(stock, 'code', 'N/A')
            name = stock.get('name', 'N/A') if isinstance(stock, dict) else getattr(stock, 'name', 'N/A')
            print(f"  - {code}: {name}")
    else:
        print("event_type: N/A (no AI extraction)")
        print("primary_theme_name: N/A")
        print("final_score: N/A")

    print(f"error_tags: {result.error_tags}")
    print(f"processing_status: {result.processing_status}")


def main():
    """运行回归测试"""
    print("新闻过滤器回归测试")
    print("="*80)

    # 初始化 Pipeline
    pipeline = SingleNewsPipeline()

    # 测试用例
    test_cases = [
        {
            'title': 'HBM概念午后异动拉升 太极实业涨停续创历史新高',
            'content': 'HBM概念午后异动拉升，太极实业涨停续创历史新高，德明利20cm涨停，江化微、华海诚科涨超10%。',
            'expected': {
                'need_ai': True,
                'event_type': 'theme_momentum',
                'primary_theme_name': 'HBM/存储芯片',
                'no_invalid_stocks': ['AI', 'AIPPI'],
            }
        },
        {
            'title': '芯片电感概念异动拉升 麦捷科技20cm涨停创历史新高',
            'content': '芯片电感概念异动拉升，麦捷科技20cm涨停创历史新高，顺络电子涨超7%。',
            'expected': {
                'need_ai': True,
                'event_type': 'theme_momentum',
                'primary_theme_name': '被动元件',
            }
        },
        {
            'title': '中国贸促会副会长李兴乾会见国际保护知识产权协会会长',
            'content': '中国贸促会副会长李兴乾6月15日在北京会见国际保护知识产权协会（AIPPI）会长尼克拉斯·克拉尔。',
            'expected': {
                'need_ai': False,
                'no_invalid_stocks': ['AIPPI'],
            }
        },
        {
            'title': '油价今晚下调了 加满一箱油能少花20元',
            'content': '国内油价今晚下调，92号汽油每升下调0.15元，加满一箱油能少花20元。',
            'expected': {
                'need_ai': False,
                'final_score_max': 30,
            }
        },
        {
            'title': '我国智能产品质量安全风险控制知识库建设取得突破',
            'content': '市场监管总局召开新闻发布会，介绍我国智能产品质量安全风险控制知识库建设情况。',
            'expected': {
                'need_ai': False,
                'final_score_max': 30,
            }
        },
        {
            'title': '主力资金监控：工业富联净买入超51亿',
            'content': '主力资金监控显示，工业富联今日净买入超51亿元，成交额突破200亿元。',
            'expected': {
                'need_ai': True,
                'event_type': 'fund_flow',
                'has_stock': '工业富联',
            }
        },
        {
            'title': '七部门：推动算力资源开放 引导平台企业联通分布式算力资源及纳管平台',
            'content': '工信部等七部门印发《推动人工智能和制造业深度融合发展的行动方案》。',
            'expected': {
                'need_ai': True,
                'event_type': 'policy_support',
                'primary_theme_name': 'AI算力',
                'final_score_min': 60,
            }
        },
        {
            'title': '长江存储出售武汉新芯39%股权',
            'content': '长江存储科技有限责任公司出售武汉新芯集成电路制造有限公司39%股权。',
            'expected': {
                'need_ai': True,
                'event_type': 'equity_transfer',
                'primary_theme_name': '存储芯片',
            }
        },
    ]

    # 运行测试
    for i, test_case in enumerate(test_cases, 1):
        title = test_case['title']
        content = test_case['content']

        # 创建 NewsItem
        news = NewsItem(
            news_id=f'test_{i}',
            source='cls',
            title=title,
            content=content,
            publish_time=datetime.now()
        )

        # 处理
        result = pipeline.process(
            news=news,
            batch_id='test_batch',
            run_id='test_run',
            is_new=True
        )

        # 打印结果
        print_result(title, result)

        # 验证期望
        expected = test_case.get('expected', {})

        # 验证 need_ai
        if 'need_ai' in expected:
            if result.need_ai != expected['need_ai']:
                print(f"❌ need_ai 不匹配: 期望 {expected['need_ai']}, 实际 {result.need_ai}")

        # 验证无效股票
        if 'no_invalid_stocks' in expected and result.final_event:
            related_stocks = getattr(result.final_event, 'related_stocks', [])
            for invalid_code in expected['no_invalid_stocks']:
                for stock in related_stocks:
                    code = stock.get('code', '') if isinstance(stock, dict) else getattr(stock, 'code', '')
                    if code == invalid_code:
                        print(f"❌ 发现无效股票代码: {invalid_code}")

    print(f"\n{'='*80}")
    print("测试完成")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
