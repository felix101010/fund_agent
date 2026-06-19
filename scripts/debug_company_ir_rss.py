"""
调试Company IR RSS（增强版）
检查RSS feed发现和解析
"""
import sys
sys.path.insert(0, 'src')

import requests
import feedparser
from fund_quant.data_sources.news.company_ir.ir_rss_utils import (
    is_probable_feed_response,
    discover_feed_urls
)


def debug_url(url: str):
    """调试单个URL"""
    print(f"\n{'='*80}")
    print(f"调试: {url}")
    print(f"{'='*80}\n")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"✓ Content Length: {len(response.content)}")
        
        # 判断是否是feed
        is_feed = is_probable_feed_response(
            response.headers.get('Content-Type', ''),
            response.text
        )
        print(f"✓ probable_feed: {is_feed}")
        
        if is_feed:
            # 尝试解析feed
            print(f"\n📡 解析Feed:")
            feed = feedparser.parse(response.content)
            print(f"  Version: {feed.version}")
            print(f"  Title: {feed.feed.get('title', 'N/A')}")
            print(f"  Entries: {len(feed.entries)}")
            
            if feed.entries:
                print(f"\n📰 第一条:")
                entry = feed.entries[0]
                print(f"  Title: {entry.get('title', 'N/A')[:80]}")
                print(f"  Link: {entry.get('link', 'N/A')}")
                print(f"  Published: {entry.get('published', 'N/A')}")
        else:
            # 尝试发现feed
            print(f"\n🔍 发现Feed:")
            discovered = discover_feed_urls(response.text, url)
            
            if discovered:
                print(f"  发现{len(discovered)}个feed:")
                for feed_url in discovered[:5]:  # 只显示前5个
                    print(f"    - {feed_url}")
                
                # 测试第一个发现的feed
                if discovered:
                    print(f"\n🧪 测试第一个发现的feed:")
                    test_feed_url = discovered[0]
                    try:
                        test_resp = requests.get(test_feed_url, headers=headers, timeout=10)
                        print(f"  URL: {test_feed_url}")
                        print(f"  Status: {test_resp.status_code}")
                        print(f"  Content-Type: {test_resp.headers.get('Content-Type')}")
                        
                        is_test_feed = is_probable_feed_response(
                            test_resp.headers.get('Content-Type', ''),
                            test_resp.text
                        )
                        print(f"  probable_feed: {is_test_feed}")
                        
                        if is_test_feed:
                            test_parsed = feedparser.parse(test_resp.content)
                            print(f"  Entries: {len(test_parsed.entries)} ✅")
                    except Exception as e:
                        print(f"  测试失败: {e}")
            else:
                print(f"  ❌ 未发现任何feed")
                
    except Exception as e:
        print(f"❌ 请求失败: {e}")


if __name__ == '__main__':
    # 测试NVDA的URLs
    print("\n" + "🎯 "*40)
    print("Company IR RSS 诊断工具")
    print("🎯 "*40)
    
    urls = [
        "https://investor.nvidia.com/investor-resources/rss/default.aspx",
        "https://nvidianews.nvidia.com/rss",
        "https://nvidianews.nvidia.com/releases.xml",
        "https://investor.nvidia.com/rss/Event.aspx?LanguageId=1"
    ]
    
    for url in urls:
        debug_url(url)
    
    print(f"\n{'='*80}")
    print("诊断完成")
    print(f"{'='*80}\n")
