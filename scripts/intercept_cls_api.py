#!/usr/bin/env python3
"""
拦截财联社API请求
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def handle_response(response):
    """处理响应"""
    url = response.url

    # 查找可能的API请求
    if 'telegraph' in url.lower() or 'api' in url.lower() or 'roll' in url.lower():
        print(f"\n发现API请求: {url}")
        print(f"状态码: {response.status}")

        try:
            if response.status == 200:
                body = response.json()
                print(f"响应数据: {json.dumps(body, ensure_ascii=False, indent=2)[:1000]}")
        except:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 监听网络请求
    page.on("response", handle_response)

    print("访问财联社电报页面...")
    page.goto("https://www.cls.cn/telegraph", wait_until="networkidle", timeout=60000)

    print("\n等待页面完全加载...")
    import time
    time.sleep(5)

    print("\n页面加载完成")

    browser.close()
