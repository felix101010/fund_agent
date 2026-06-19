"""
测试Company IR标准化器
"""
import pytest

from fund_quant.data_sources.news.company_ir import (
    normalize_ir_item,
    get_ir_company_config
)


class TestIRNormalizer:
    """测试IR标准化器"""

    def test_normalize_basic_fields(self):
        """测试基础字段标准化"""
        config = get_ir_company_config('NVDA')

        raw_item = {
            'title': 'NVIDIA Announces Financial Results',
            'link': 'https://investor.nvidia.com/news/123',
            'published': 'Mon, 15 Jan 2024 10:30:00 GMT',
            'summary': 'Revenue and earnings summary',
            'source_detail': 'ir_rss'
        }

        result = normalize_ir_item('NVDA', config, raw_item)

        # 检查字段完整性
        assert result['source'] == 'company_ir'
        assert result['source_detail'] == 'ir_rss'
        assert result['ticker'] == 'NVDA'
        assert result['company_name'] == 'NVIDIA'
        assert result['title'] == 'NVIDIA Announces Financial Results'
        assert result['url'] == 'https://investor.nvidia.com/news/123'
        assert result['summary'] == 'Revenue and earnings summary'
        assert 'news_id' in result
        assert 'publish_time' in result
        assert 'raw' in result

    def test_normalize_with_article_detail(self):
        """测试带文章详情的标准化"""
        config = get_ir_company_config('NVDA')

        raw_item = {
            'title': 'Test Title',
            'link': 'https://test.com/123',
            'published': 'Mon, 15 Jan 2024 10:30:00 GMT',
            'summary': 'Short summary',
            'source_detail': 'ir_rss'
        }

        article_detail = {
            'content': 'Full article content with more details',
            'attachments': [
                {'type': 'pdf', 'title': 'Q1 Report', 'url': 'https://...'}
            ]
        }

        result = normalize_ir_item('NVDA', config, raw_item, article_detail)

        # content应该优先使用article_detail
        assert result['content'] == 'Full article content with more details'
        assert len(result['attachments']) == 1
        assert result['attachments'][0]['type'] == 'pdf'

    def test_normalize_news_id_stability(self):
        """测试news_id稳定性"""
        config = get_ir_company_config('NVDA')

        raw_item = {
            'title': 'Test',
            'link': 'https://test.com/123',
            'published': 'Mon, 15 Jan 2024 10:30:00 GMT',
            'summary': 'Summary'
        }

        result1 = normalize_ir_item('NVDA', config, raw_item)
        result2 = normalize_ir_item('NVDA', config, raw_item)

        # 相同输入应该生成相同news_id
        assert result1['news_id'] == result2['news_id']
        assert result1['news_id'].startswith('company_ir_NVDA_')

    def test_normalize_publish_time_format(self):
        """测试publish_time格式"""
        config = get_ir_company_config('NVDA')

        raw_item = {
            'title': 'Test',
            'link': 'https://test.com/123',
            'published': 'Mon, 15 Jan 2024 10:30:00 GMT',
            'summary': 'Summary'
        }

        result = normalize_ir_item('NVDA', config, raw_item)

        # 应该是ISO格式
        assert 'T' in result['publish_time']
        assert result['publish_time'].count('-') >= 2  # YYYY-MM-DD

    def test_normalize_missing_fields(self):
        """测试缺失字段的处理"""
        config = get_ir_company_config('NVDA')

        # 最小化的raw_item
        raw_item = {}

        # 不应该崩溃
        result = normalize_ir_item('NVDA', config, raw_item)

        assert result['source'] == 'company_ir'
        assert result['ticker'] == 'NVDA'
        assert result['title'] == ''
        assert result['content'] == ''
        assert 'news_id' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
