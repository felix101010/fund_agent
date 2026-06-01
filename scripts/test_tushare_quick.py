#!/usr/bin/env python
"""
快速测试 Tushare 配置是否正确
只测试基础连接，不需要完整依赖
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_env():
    """测试环境变量"""
    print("=" * 60)
    print("1. 测试环境变量")
    print("=" * 60)

    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv("TUSHARE_TOKEN")
    api_url = os.getenv("TUSHARE_API_URL")

    if token:
        print(f"✓ TUSHARE_TOKEN: {token[:10]}...{token[-10:]}")
    else:
        print("✗ TUSHARE_TOKEN 未配置")
        return False

    if api_url:
        print(f"✓ TUSHARE_API_URL: {api_url}")
    else:
        print("  TUSHARE_API_URL 未配置（将使用官方地址）")

    return True


def test_tushare_import():
    """测试 tushare 导入"""
    print("\n" + "=" * 60)
    print("2. 测试 Tushare 导入")
    print("=" * 60)

    try:
        import tushare as ts
        print(f"✓ Tushare 版本: {ts.__version__}")
        return True
    except ImportError as e:
        print(f"✗ Tushare 导入失败: {e}")
        return False


def test_tushare_connection():
    """测试 Tushare 连接"""
    print("\n" + "=" * 60)
    print("3. 测试 Tushare 连接")
    print("=" * 60)

    try:
        from fund_quant.market.tushare_provider import get_tushare_pro

        pro = get_tushare_pro()
        print("✓ Tushare Pro API 初始化成功")

        # 简单测试：获取交易日历（轻量接口）
        df = pro.trade_cal(exchange='SSE', start_date='20260101', end_date='20260110')

        if df is not None and len(df) > 0:
            print(f"✓ API 调用成功，获取 {len(df)} 条交易日历数据")
            return True
        else:
            print("⚠ API 调用成功但返回数据为空")
            return False

    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Tushare 配置测试")
    print("=" * 60 + "\n")

    results = []

    # 测试环境变量
    results.append(("环境变量", test_env()))

    # 测试导入
    results.append(("Tushare导入", test_tushare_import()))

    # 测试连接
    if results[-1][1]:  # 如果导入成功才测试连接
        results.append(("Tushare连接", test_tushare_connection()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n🎉 所有测试通过！Tushare 配置成功！")
        print("\n下一步:")
        print("  python scripts/test_tushare.py --basic")
        sys.exit(0)
    else:
        print("\n⚠ 部分测试失败，请检查配置")
        sys.exit(1)
