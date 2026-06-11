#!/usr/bin/env python3
"""
采集财联社新闻并写入数据库
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data_sources.news import NewsService


def main():
    """脚本入口，只做调度"""
    service = NewsService(limit=50)
    df = service.fetch_and_store()

    if df is not None:
        print(f"\n成功采集 {len(df)} 条新闻")
    else:
        print("\n采集失败")


if __name__ == "__main__":
    main()
