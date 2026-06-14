"""
巨潮资讯采集器
基于probe_cninfo_api.py探针验证的成功组合实现
"""
import time
import requests
from datetime import datetime, timedelta
from typing import List, Optional
from fund_quant.data_sources.announcements.announcement_models import RawAnnouncement


class CninfoCollector:
    """
    巨潮资讯采集器

    成功组合（探针验证）：
    - URL: https://www.cninfo.com.cn/new/hisAnnouncement/query
    - 方法: POST (data=params, 不是json=params)
    - 先访问首页获取Cookie
    - column: 'szse' 或空字符串
    - Content-Type: application/x-www-form-urlencoded
    """

    def __init__(self, base_url: str = "https://www.cninfo.com.cn"):
        """
        初始化采集器

        Args:
            base_url: 巨潮资讯基础URL
        """
        self.base_url = base_url
        self.api_url = f"{base_url}/new/hisAnnouncement/query"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': f'{base_url}/new/index',
            'Origin': base_url
        })
        self._init_session()

    def _init_session(self):
        """初始化session：访问首页获取Cookie"""
        try:
            response = self.session.get(f'{self.base_url}/new/index', timeout=10)
            if response.status_code == 200:
                print(f"✅ Session初始化成功")
        except Exception as e:
            print(f"⚠️  Session初始化失败: {e}")

    def fetch_latest(self, limit: int = 50) -> List[RawAnnouncement]:
        """
        获取最新公告列表

        Args:
            limit: 获取数量

        Returns:
            公告列表
        """
        print(f"📡 采集最新公告（limit={limit}）...")

        # 计算需要的页数
        page_size = 30
        num_pages = (limit + page_size - 1) // page_size

        all_announcements = []

        for page_num in range(1, num_pages + 1):
            try:
                # 使用探针验证的成功参数
                params = {
                    'pageNum': str(page_num),
                    'pageSize': str(page_size),
                    'column': 'szse',  # 深交所（探针验证成功）
                    'tabName': 'fulltext',
                    'plate': '',
                    'stock': '',
                    'searchkey': '',
                    'secid': '',
                    'category': '',
                    'trade': '',
                    'seDate': '',  # 空表示全部日期
                    'sortName': '',
                    'sortType': '',
                    'isHLtitle': 'true'
                }

                # POST请求（探针验证：必须用POST + data）
                response = self.session.post(
                    self.api_url,
                    data=params,  # 注意：用data不是json
                    timeout=15
                )

                if response.status_code != 200:
                    print(f"⚠️  第{page_num}页请求失败: HTTP {response.status_code}")
                    break

                data = response.json()

                if not data or 'announcements' not in data:
                    print(f"⚠️  第{page_num}页: 无公告数据")
                    break

                announcements_data = data['announcements']

                if not announcements_data:
                    print(f"  第{page_num}页: 无更多公告")
                    break

                for item in announcements_data:
                    announcement = self._parse_announcement(item)
                    if announcement:
                        all_announcements.append(announcement)

                    if len(all_announcements) >= limit:
                        break

                print(f"  第{page_num}页: 采集 {len(announcements_data)} 条")

                if len(all_announcements) >= limit:
                    break

                # 避免请求过快
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                print(f"⚠️  第{page_num}页网络错误: {e}")
                break
            except Exception as e:
                print(f"⚠️  第{page_num}页采集失败: {e}")
                break

        print(f"✅ 共采集 {len(all_announcements)} 条公告")
        return all_announcements[:limit]

    def fetch_by_date_range(
        self,
        start_date: str,
        end_date: str,
        page_size: int = 30
    ) -> List[RawAnnouncement]:
        """
        按日期范围获取公告

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            page_size: 每页数量

        Returns:
            公告列表
        """
        print(f"📡 采集公告（{start_date} ~ {end_date}）...")

        all_announcements = []
        page_num = 1
        max_pages = 20

        while page_num <= max_pages:
            try:
                params = {
                    'pageNum': str(page_num),
                    'pageSize': str(page_size),
                    'column': '',  # 全市场（探针验证：空字符串可用）
                    'tabName': 'fulltext',
                    'plate': '',
                    'stock': '',
                    'searchkey': '',
                    'secid': '',
                    'category': '',
                    'trade': '',
                    'seDate': f"{start_date}~{end_date}",  # 日期范围
                    'sortName': '',
                    'sortType': '',
                    'isHLtitle': 'true'
                }

                response = self.session.post(self.api_url, data=params, timeout=15)

                if response.status_code != 200:
                    print(f"⚠️  第{page_num}页请求失败: HTTP {response.status_code}")
                    break

                data = response.json()

                if not data or 'announcements' not in data:
                    break

                announcements_data = data['announcements']

                if not announcements_data:
                    break

                for item in announcements_data:
                    announcement = self._parse_announcement(item)
                    if announcement:
                        all_announcements.append(announcement)

                print(f"  第{page_num}页: 采集 {len(announcements_data)} 条")

                page_num += 1
                time.sleep(1)

            except Exception as e:
                print(f"⚠️  第{page_num}页采集失败: {e}")
                break

        print(f"✅ 共采集 {len(all_announcements)} 条公告")
        return all_announcements

    def fetch_by_stock(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[RawAnnouncement]:
        """
        按股票代码获取公告

        Args:
            stock_code: 股票代码（支持：000001, 600000等）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            公告列表
        """
        # 规范化股票代码（去掉.SZ/.SH后缀）
        stock_code_clean = stock_code.split('.')[0]

        print(f"📡 采集股票公告（{stock_code_clean}）...")

        all_announcements = []
        page_num = 1
        max_pages = 10

        while page_num <= max_pages:
            try:
                params = {
                    'pageNum': str(page_num),
                    'pageSize': '30',
                    'column': '',
                    'tabName': 'fulltext',
                    'plate': '',
                    'stock': stock_code_clean,  # 股票代码
                    'searchkey': '',
                    'secid': '',
                    'category': '',
                    'trade': '',
                    'seDate': '',
                    'sortName': '',
                    'sortType': '',
                    'isHLtitle': 'true'
                }

                # 如果有日期范围
                if start_date and end_date:
                    params['seDate'] = f"{start_date}~{end_date}"

                response = self.session.post(self.api_url, data=params, timeout=15)

                if response.status_code != 200:
                    print(f"⚠️  第{page_num}页请求失败: HTTP {response.status_code}")
                    break

                data = response.json()

                if not data or 'announcements' not in data:
                    break

                announcements_data = data['announcements']

                if not announcements_data:
                    break

                for item in announcements_data:
                    announcement = self._parse_announcement(item)
                    if announcement:
                        all_announcements.append(announcement)

                print(f"  第{page_num}页: 采集 {len(announcements_data)} 条")

                page_num += 1
                time.sleep(1)

            except Exception as e:
                print(f"⚠️  第{page_num}页采集失败: {e}")
                break

        print(f"✅ 共采集 {len(all_announcements)} 条公告")
        return all_announcements

    def _parse_announcement(self, item: dict) -> Optional[RawAnnouncement]:
        """
        解析单条公告数据

        Args:
            item: API返回的公告数据

        Returns:
            RawAnnouncement或None
        """
        try:
            # 提取字段
            announcement_id = item.get('announcementId', '')
            stock_code = item.get('secCode', '')
            stock_name = item.get('secName', '')
            title = item.get('announcementTitle', '')
            announcement_type_raw = item.get('announcementType', '')
            publish_time_str = item.get('announcementTime', '')

            # 解析时间
            publish_time = None
            if publish_time_str:
                try:
                    # 时间戳（毫秒）
                    if isinstance(publish_time_str, (int, float)):
                        publish_time = datetime.fromtimestamp(publish_time_str / 1000)
                    else:
                        # 字符串格式
                        publish_time = datetime.strptime(publish_time_str, '%Y-%m-%d %H:%M:%S')
                except:
                    pass

            # PDF URL
            adj_url = item.get('adjunctUrl', '')
            pdf_url = f"http://static.cninfo.com.cn/{adj_url}" if adj_url else ""

            # 公告URL
            url = f"http://www.cninfo.com.cn/new/disclosure/detail?plate=&orgId=&stockCode={stock_code}&announcementId={announcement_id}"

            # 添加市场后缀
            if stock_code and '.' not in stock_code:
                if stock_code.startswith('6'):
                    stock_code = f"{stock_code}.SH"
                elif stock_code.startswith(('0', '3')):
                    stock_code = f"{stock_code}.SZ"
                elif stock_code.startswith(('8', '4')):
                    stock_code = f"{stock_code}.BJ"

            return RawAnnouncement(
                announcement_id=announcement_id,
                source="cninfo",
                stock_code=stock_code,
                stock_name=stock_name,
                title=title,
                announcement_type_raw=announcement_type_raw,
                publish_time=publish_time,
                url=url,
                pdf_url=pdf_url,
                content="",  # 标题级，暂不提取全文
                file_path="",
                created_at=datetime.now()
            )

        except Exception as e:
            print(f"⚠️  解析公告失败: {e}")
            return None


__all__ = ['CninfoCollector']
