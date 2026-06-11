#!/usr/bin/env python3
"""
调试财联社页面结构
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("访问财联社电报页面...")
    page.goto("https://www.cls.cn/telegraph", wait_until="domcontentloaded", timeout=30000)

    import time
    time.sleep(5)

    # 获取页面HTML
    html = page.content()

    # 保存到文件
    with open("/tmp/cls_page.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("页面HTML已保存到 /tmp/cls_page.html")

    # 尝试查找新闻元素
    print("\n尝试查找新闻元素...")

    # 查找所有可能的class
    all_classes = page.evaluate("""
        () => {
            const elements = document.querySelectorAll('*');
            const classes = new Set();
            elements.forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    el.className.split(' ').forEach(c => {
                        if (c.includes('telegraph') || c.includes('news') || c.includes('item') || c.includes('list')) {
                            classes.add(c);
                        }
                    });
                }
            });
            return Array.from(classes);
        }
    """)

    print(f"\n找到相关class: {all_classes}")

    browser.close()
