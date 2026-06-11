#!/usr/bin/env python3
"""
直接测试ClickHouse插入
"""
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data.storage.clickhouse_client import ClickHouseClient

client = ClickHouseClient()

# 测试数据
test_data = [{
    'news_id': 'test_wallstreetcn_001',
    'source': 'wallstreetcn',
    'publish_time': datetime(2026, 6, 2, 9, 0, 0),
    'title': '测试标题',
    'content': '测试内容',
    'url': 'https://test.com',
    'raw_json': '{}',
    'first_seen_time': datetime.now(),
    'delay_seconds': 100,
    'created_at': datetime.now(),
}]

print("测试数据:")
print(test_data[0])

print("\n开始插入...")
try:
    client.insert_many('raw_news', test_data)
    print("✓ 插入成功")
except Exception as e:
    print(f"✗ 插入失败: {e}")
    import traceback
    traceback.print_exc()
