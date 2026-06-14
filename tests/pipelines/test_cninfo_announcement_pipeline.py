"""
巨潮资讯公告处理流程测试
"""
import pytest
from fund_quant.data_sources.announcements.announcement_models import RawAnnouncement
from fund_quant.nlp.announcements.announcement_filter import AnnouncementFilter
from fund_quant.pipelines.announcement_pipeline import SingleAnnouncementPipeline
from datetime import datetime


class TestCninfoAnnouncementPipeline:
    """巨潮资讯公告处理流程测试"""

    def test_major_contract_announcement(self):
        """测试：重大合同公告 → action=analyze, need_ai=True, need_pdf=True"""
        announcement = RawAnnouncement(
            announcement_id="test_001",
            stock_code="000001.SZ",
            stock_name="平安银行",
            title="关于签订重大合同的公告",
            announcement_type_raw="重大合同公告",
            publish_time=datetime.now()
        )

        filter_obj = AnnouncementFilter()
        result = filter_obj.filter(announcement)

        assert result.action == "analyze"
        assert result.need_ai == True
        assert result.need_pdf == True
        assert result.announcement_type == "major_contract"

    def test_bid_winning_announcement(self):
        """测试：中标公告 → action=analyze"""
        announcement = RawAnnouncement(
            announcement_id="test_002",
            stock_code="600000.SH",
            stock_name="浦发银行",
            title="关于项目中标的公告",
            announcement_type_raw="其他公告",
            publish_time=datetime.now()
        )

        filter_obj = AnnouncementFilter()
        result = filter_obj.filter(announcement)

        assert result.action == "analyze"
        assert result.need_ai == True

    def test_inquiry_letter_announcement(self):
        """测试：问询函/监管函 → action=risk_review"""
        announcement = RawAnnouncement(
            announcement_id="test_003",
            stock_code="000002.SZ",
            stock_name="万科A",
            title="关于深交所问询函的回复公告",
            announcement_type_raw="问询函回复",
            publish_time=datetime.now()
        )

        filter_obj = AnnouncementFilter()
        result = filter_obj.filter(announcement)

        assert result.action == "risk_review"
        assert result.need_ai == True

    def test_shareholder_meeting_notice(self):
        """测试：股东大会通知 → action=archive, need_ai=False"""
        announcement = RawAnnouncement(
            announcement_id="test_004",
            stock_code="600036.SH",
            stock_name="招商银行",
            title="关于召开股东大会的通知",
            announcement_type_raw="股东大会通知",
            publish_time=datetime.now()
        )

        filter_obj = AnnouncementFilter()
        result = filter_obj.filter(announcement)

        assert result.action == "archive"
        assert result.need_ai == False
        assert result.need_pdf == False

    def test_annual_report_watch(self):
        """测试：年报/季报 → action=watch, 当前阶段不AI"""
        announcement = RawAnnouncement(
            announcement_id="test_005",
            stock_code="601318.SH",
            stock_name="中国平安",
            title="2025年年度报告",
            announcement_type_raw="年度报告",
            publish_time=datetime.now()
        )

        filter_obj = AnnouncementFilter()
        result = filter_obj.filter(announcement)

        assert result.action == "watch"
        assert result.need_ai == False

    def test_stock_binding(self):
        """测试：公告天然绑定stock_code/stock_name，related_stocks必须包含该股票"""
        announcement = RawAnnouncement(
            announcement_id="test_006",
            stock_code="600519.SH",
            stock_name="贵州茅台",
            title="关于签订重大合同的公告",
            publish_time=datetime.now()
        )

        pipeline = SingleAnnouncementPipeline()
        result = pipeline.process(announcement, "test_batch")

        assert result.stock_code == "600519.SH"
        assert result.stock_name == "贵州茅台"
        if result.final_event:
            related_stocks = result.final_event.get('related_stocks', [])
            assert len(related_stocks) == 1
            assert related_stocks[0]['code'] == "600519.SH"

    def test_single_failure_not_break_batch(self):
        """测试：单条失败不影响batch"""
        # 创建一个会导致某些字段缺失的异常公告
        announcement = RawAnnouncement(
            announcement_id="test_007",
            stock_code="",  # 故意缺失
            stock_name="",
            title="测试公告",
            publish_time=datetime.now()
        )

        pipeline = SingleAnnouncementPipeline()
        result = pipeline.process(announcement, "test_batch")

        # 即使stock_code缺失，也应该返回结果，而不是抛异常
        assert result.announcement_id == "test_007"
        assert 'stock_missing' in result.error_tags


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
