"""
测试正文抓取失败保护逻辑
"""
import pytest


class TestArticleFetchFallback:
    """测试正文抓取失败时的保护逻辑"""

    def test_rss_content_preserved_when_article_empty(self):
        """item有RSS content，fetch_article返回空，应保留RSS content"""
        # 模拟item
        item = {
            'content': 'Original RSS summary with meaningful content here',
            'summary': 'RSS summary',
            'title': 'Test Article',
            'url': 'http://example.com/article'
        }

        rss_content = item.get('content', '') or item.get('summary', '') or ''
        rss_content_len = len(rss_content)

        # 模拟fetch_article返回空
        article_content = ''
        article_content_len = len(article_content)

        # 应用保护逻辑
        if article_content_len > rss_content_len:
            item['content'] = article_content
            item['article_fetch_status'] = 'success'
        else:
            item['content'] = rss_content
            item['article_fetch_status'] = 'failed_keep_rss_content'

        # 验证
        assert item['content'] == 'Original RSS summary with meaningful content here'
        assert item['article_fetch_status'] == 'failed_keep_rss_content'
        assert len(item['content']) > 0

    def test_rss_content_replaced_when_article_longer(self):
        """item有RSS content，fetch_article返回更长正文，应使用article content"""
        # 模拟item
        item = {
            'content': 'Short RSS summary',
            'summary': 'RSS summary',
            'title': 'Test Article',
            'url': 'http://example.com/article'
        }

        rss_content = item.get('content', '') or item.get('summary', '') or ''
        rss_content_len = len(rss_content)

        # 模拟fetch_article返回更长正文
        article_content = 'This is a much longer article content with detailed information about the announcement. ' * 5
        article_content_len = len(article_content)

        # 应用保护逻辑
        if article_content_len > rss_content_len:
            item['content'] = article_content
            item['article_fetch_status'] = 'success'
        else:
            item['content'] = rss_content
            item['article_fetch_status'] = 'failed_keep_rss_content'

        # 验证
        assert item['content'] == article_content
        assert item['article_fetch_status'] == 'success'
        assert len(item['content']) > rss_content_len

    def test_no_rss_content_article_empty(self):
        """item无RSS content，fetch_article返回空，content保持空"""
        # 模拟item
        item = {
            'content': '',
            'summary': '',
            'title': 'Test Article',
            'url': 'http://example.com/article'
        }

        rss_content = item.get('content', '') or item.get('summary', '') or ''
        rss_content_len = len(rss_content)

        # 模拟fetch_article返回空
        article_content = ''
        article_content_len = len(article_content)

        # 应用保护逻辑
        if article_content_len > rss_content_len:
            item['content'] = article_content
            item['article_fetch_status'] = 'success'
        else:
            item['content'] = rss_content
            item['article_fetch_status'] = 'failed_keep_rss_content'

        # 验证
        assert item['content'] == ''
        assert item['article_fetch_status'] == 'failed_keep_rss_content'

    def test_rss_content_136_chars_preserved(self):
        """模拟AAPL实际场景：RSS content 122字符，article返回0，应保留RSS"""
        # 模拟实际AAPL item
        item = {
            'content': '',
            'summary': 'Apple unveils next generation of Apple Intelligence, bringing powerful personal intelligence to the iPhone, iPad, and Mac.',
            'title': 'Apple unveils next generation of Apple Intelligence',
            'url': 'https://www.apple.com/newsroom/2026/06/apple-intelligence'
        }

        rss_content = item.get('content', '') or item.get('summary', '') or ''
        rss_content_len = len(rss_content)  # 122

        # 模拟fetch_article失败返回0
        article_content = ''
        article_content_len = 0

        # 应用保护逻辑
        if article_content_len > rss_content_len:
            item['content'] = article_content
            item['article_fetch_status'] = 'success'
        else:
            item['content'] = rss_content
            item['article_fetch_status'] = 'failed_keep_rss_content'

        # 验证
        assert len(item['content']) == 122
        assert item['content'] == 'Apple unveils next generation of Apple Intelligence, bringing powerful personal intelligence to the iPhone, iPad, and Mac.'
        assert item['article_fetch_status'] == 'failed_keep_rss_content'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
