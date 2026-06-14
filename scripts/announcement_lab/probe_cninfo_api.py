"""
巨潮资讯免费公告接口探针
用于排查HTTP 500问题：参数、请求方式、会话/Cookie、接口可用性
"""
import argparse
import time
import json
import csv
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any


class CninfoApiProbe:
    """巨潮资讯API探针"""

    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.test_id_counter = 0

    def probe(
        self,
        mode: str = 'quick',
        stock_code: str = None,
        days: int = 7
    ):
        """
        探测巨潮API

        Args:
            mode: quick/full
            stock_code: 股票代码（可选）
            days: 日期范围天数
        """
        print("=" * 80)
        print("🔍 巨潮资讯公告接口探针")
        print("=" * 80)
        print(f"模式: {mode}")
        print(f"股票: {stock_code or '全市场'}")
        print(f"日期范围: 最近{days}天")
        print("=" * 80)

        if mode == 'quick':
            self._probe_quick(stock_code, days)
        elif mode == 'full':
            self._probe_full(stock_code, days)
        elif mode == 'stock' and stock_code:
            self._probe_stock(stock_code, days)

        # 保存结果
        self._save_results()

        # 分析结果
        self._analyze_results()

    def _probe_quick(self, stock_code: str, days: int):
        """快速模式：只测试最小参数组合"""
        print("\n🔍 快速模式：测试最小参数组合\n")

        # 测试组合1: HTTPS + 访问首页 + szse
        self._test_combination(
            url="https://www.cninfo.com.cn/new/hisAnnouncement/query",
            with_session_home=True,
            column="szse",
            plate="",
            category="",
            stock=stock_code or "",
            days=days
        )

        time.sleep(2)

        # 测试组合2: HTTP + 不访问首页 + 空column
        self._test_combination(
            url="http://www.cninfo.com.cn/new/hisAnnouncement/query",
            with_session_home=False,
            column="",
            plate="",
            category="",
            stock=stock_code or "",
            days=days
        )

    def _probe_full(self, stock_code: str, days: int):
        """完整模式：测试多个参数组合"""
        print("\n🔍 完整模式：测试多个参数组合\n")

        urls = [
            "https://www.cninfo.com.cn/new/hisAnnouncement/query",
            "http://www.cninfo.com.cn/new/hisAnnouncement/query"
        ]

        with_session_homes = [True, False]
        columns = ["szse", "sse", "szse,sse", ""]
        plates = ["", "szmb", "szcy"]

        test_count = 0
        max_tests = 12  # 限制测试数量

        for url in urls:
            for with_home in with_session_homes:
                for column in columns:
                    for plate in plates:
                        if test_count >= max_tests:
                            print(f"⚠️  已达到最大测试数({max_tests})，停止")
                            return

                        self._test_combination(
                            url=url,
                            with_session_home=with_home,
                            column=column,
                            plate=plate,
                            category="",
                            stock=stock_code or "",
                            days=days
                        )

                        test_count += 1
                        time.sleep(2)  # 避免高频请求

    def _probe_stock(self, stock_code: str, days: int):
        """按股票测试"""
        print(f"\n🔍 股票模式：测试股票 {stock_code}\n")

        # 清理股票代码
        stock_clean = stock_code.replace('.SZ', '').replace('.SH', '').replace('.BJ', '')

        # 测试1: 原始代码
        self._test_combination(
            url="https://www.cninfo.com.cn/new/hisAnnouncement/query",
            with_session_home=True,
            column="",
            plate="",
            category="",
            stock=stock_clean,
            days=days
        )

        time.sleep(2)

        # 测试2: 带column
        self._test_combination(
            url="https://www.cninfo.com.cn/new/hisAnnouncement/query",
            with_session_home=True,
            column="szse" if stock_clean.startswith(('0', '3')) else "sse",
            plate="",
            category="",
            stock=stock_clean,
            days=days
        )

    def _test_combination(
        self,
        url: str,
        with_session_home: bool,
        column: str,
        plate: str,
        category: str,
        stock: str,
        days: int
    ):
        """测试单个参数组合"""
        self.test_id_counter += 1
        test_id = f"test_{self.test_id_counter:03d}"

        print(f"\n{test_id}:")
        print(f"  URL: {url}")
        print(f"  访问首页: {with_session_home}")
        print(f"  column: '{column}', plate: '{plate}', stock: '{stock}'")

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        se_date = f"{start_date.strftime('%Y-%m-%d')}~{end_date.strftime('%Y-%m-%d')}"

        result = {
            'test_id': test_id,
            'url': url,
            'with_session_home': with_session_home,
            'column': column,
            'plate': plate,
            'category': category,
            'stock': stock,
            'seDate': se_date,
            'status_code': None,
            'is_json': False,
            'success': False,
            'announcements_count': 0,
            'error_message': '',
            'response_preview': ''
        }

        try:
            # 1. 如果需要，先访问首页
            if with_session_home:
                try:
                    home_response = self.session.get(
                        'https://www.cninfo.com.cn/new/index',
                        timeout=10
                    )
                    print(f"  首页访问: HTTP {home_response.status_code}")
                    time.sleep(1)
                except Exception as e:
                    print(f"  首页访问失败: {e}")

            # 2. 准备请求
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'https://www.cninfo.com.cn/new/index',
                'Origin': 'https://www.cninfo.com.cn'
            }

            params = {
                'pageNum': '1',
                'pageSize': '30',
                'column': column,
                'tabName': 'fulltext',
                'plate': plate,
                'stock': stock,
                'searchkey': '',
                'secid': '',
                'category': category,
                'trade': '',
                'seDate': se_date,
                'sortName': '',
                'sortType': '',
                'isHLtitle': 'true'
            }

            # 3. POST请求
            response = self.session.post(
                url,
                data=params,
                headers=headers,
                timeout=15
            )

            result['status_code'] = response.status_code
            result['response_preview'] = response.text[:300]

            print(f"  状态码: {response.status_code}")

            # 4. 解析响应
            if response.status_code == 200:
                try:
                    data = response.json()
                    result['is_json'] = True

                    if 'announcements' in data:
                        announcements = data.get('announcements', [])
                        result['announcements_count'] = len(announcements)
                        result['success'] = True

                        print(f"  ✅ 成功! 获取 {len(announcements)} 条公告")

                        # 打印前3条
                        for i, ann in enumerate(announcements[:3], 1):
                            print(f"    {i}. [{ann.get('secCode')}] {ann.get('secName')}")
                            print(f"       {ann.get('announcementTitle', '')[:50]}")

                    else:
                        result['error_message'] = 'no_announcements_field'
                        print(f"  ⚠️  JSON无announcements字段")

                except json.JSONDecodeError:
                    result['error_message'] = 'json_decode_error'
                    print(f"  ⚠️  JSON解析失败")
                    print(f"  响应预览: {response.text[:200]}")

            elif response.status_code == 500:
                result['error_message'] = 'http_500_server_error_or_bad_params'
                print(f"  ❌ HTTP 500 - 服务器错误或参数错误")

            else:
                result['error_message'] = f'http_{response.status_code}'
                print(f"  ⚠️  HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            result['error_message'] = 'timeout'
            print(f"  ❌ 请求超时")

        except Exception as e:
            result['error_message'] = str(e)
            print(f"  ❌ 异常: {e}")

        self.test_results.append(result)

    def _save_results(self):
        """保存结果"""
        output_dir = Path('data/review/cninfo_probe')
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # JSON
        json_path = output_dir / f'cninfo_probe_{timestamp}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 JSON: {json_path}")

        # CSV
        csv_path = output_dir / f'cninfo_probe_{timestamp}.csv'
        if self.test_results:
            fieldnames = [
                'test_id', 'url', 'with_session_home', 'column', 'plate',
                'category', 'stock', 'seDate', 'status_code', 'is_json',
                'success', 'announcements_count', 'error_message', 'response_preview'
            ]

            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.test_results)
            print(f"💾 CSV: {csv_path}")

    def _analyze_results(self):
        """分析结果"""
        print("\n" + "=" * 80)
        print("📊 探测结果分析")
        print("=" * 80)

        total = len(self.test_results)
        success_count = sum(1 for r in self.test_results if r['success'])
        http_500_count = sum(1 for r in self.test_results if r['status_code'] == 500)

        print(f"总测试数: {total}")
        print(f"成功: {success_count}")
        print(f"HTTP 500: {http_500_count}")
        print(f"其他失败: {total - success_count - http_500_count}")

        # 找出成功的组合
        successful = [r for r in self.test_results if r['success']]

        if successful:
            print(f"\n✅ 找到 {len(successful)} 个可用巨潮公告查询组合\n")

            for r in successful:
                print(f"推荐组合 {r['test_id']}:")
                print(f"  URL: {r['url']}")
                print(f"  访问首页: {r['with_session_home']}")
                print(f"  column: '{r['column']}'")
                print(f"  plate: '{r['plate']}'")
                print(f"  获取数: {r['announcements_count']} 条")
                print()

            print("💡 后续TODO: 基于成功组合实现 CninfoCollector.fetch_latest()")

        else:
            print("\n❌ 所有组合均失败\n")
            print("可能原因:")
            print("  1. API接口已变更或不可用")
            print("  2. 需要特定Cookie/Token（但探针不应破解）")
            print("  3. IP被限制（需等待或更换网络）")
            print("  4. 请求参数组合均不正确")
            print("\n建议:")
            print("  - 等待一段时间后重试")
            print("  - 使用代理或更换网络")
            print("  - 考虑使用第三方免费API（akshare/tushare）")


def main():
    parser = argparse.ArgumentParser(description='巨潮资讯公告接口探针')

    parser.add_argument('--quick', action='store_true', help='快速模式（最小参数组合）')
    parser.add_argument('--full', action='store_true', help='完整模式（多参数组合）')
    parser.add_argument('--stock', type=str, help='按股票测试（如：300308）')
    parser.add_argument('--days', type=int, default=7, help='日期范围天数（默认7天）')

    args = parser.parse_args()

    # 确定模式
    if args.stock:
        mode = 'stock'
    elif args.full:
        mode = 'full'
    else:
        mode = 'quick'

    probe = CninfoApiProbe()
    probe.probe(mode=mode, stock_code=args.stock, days=args.days)


if __name__ == '__main__':
    main()
