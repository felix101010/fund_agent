#!/usr/bin/env python3
"""
调试数据结构
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data_sources.news.wallstreetcn_rss_collector import WallstreetcnRssCollector

collector = WallstreetcnRssCollector()
df = collector.fetch_latest()

print(f"\nDataFrame shape: {df.shape}")
print(f"\nDataFrame columns: {df.columns.tolist()}")
print(f"\nDataFrame dtypes:")
print(df.dtypes)

print(f"\n第一条记录:")
first_record = df.iloc[0].to_dict()
for key, value in first_record.items():
    print(f"  {key}: {type(value).__name__} = {str(value)[:100]}")
