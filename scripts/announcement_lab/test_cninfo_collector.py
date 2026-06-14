"""
测试巨潮资讯采集器
"""
from fund_quant.data_sources.announcements import CninfoCollector
from fund_quant.data_sources.announcements.announcement_models import RawAnnouncement
from datetime import datetime


def test_with_mock_data():
    """使用mock数据测试pipeline"""
    print("=" * 80)
    print("使用Mock数据测试Pipeline")
    print("=" * 80)

    # 创建mock公告
    mock_announcements = [
        RawAnnouncement(
            announcement_id="mock_001",
            source="cninfo",
            stock_code="000001.SZ",
            stock_name="平安银行",
            title="关于签订重大合同的公告",
            announcement_type_raw="重大合同公告",
            publish_time=datetime.now(),
            url="http://www.cninfo.com.cn/mock",
            pdf_url="http://static.cninfo.com.cn/mock.pdf",
            content="",
            file_path="",
            created_at=datetime.now()
        ),
        RawAnnouncement(
            announcement_id="mock_002",
            source="cninfo",
            stock_code="600000.SH",
            stock_name="浦发银行",
            title="关于项目中标的公告",
            announcement_type_raw="其他公告",
            publish_time=datetime.now(),
            url="http://www.cninfo.com.cn/mock",
            pdf_url="http://static.cninfo.com.cn/mock.pdf",
            content="",
            file_path="",
            created_at=datetime.now()
        ),
        RawAnnouncement(
            announcement_id="mock_003",
            source="cninfo",
            stock_code="000002.SZ",
            stock_name="万科A",
            title="关于深交所问询函的回复公告",
            announcement_type_raw="问询函回复",
            publish_time=datetime.now(),
            url="http://www.cninfo.com.cn/mock",
            pdf_url="http://static.cninfo.com.cn/mock.pdf",
            content="",
            file_path="",
            created_at=datetime.now()
        ),
    ]

    return mock_announcements


def test_real_api():
    """测试真实API"""
    print("=" * 80)
    print("测试巨潮资讯真实API")
    print("=" * 80)

    collector = CninfoCollector()

    try:
        announcements = collector.fetch_latest(limit=5)

        if announcements:
            print(f"\n✅ 成功采集 {len(announcements)} 条公告\n")
            for i, ann in enumerate(announcements[:3], 1):
                print(f"{i}. [{ann.stock_code}] {ann.stock_name}")
                print(f"   {ann.title}")
                print(f"   发布时间: {ann.publish_time}")
                print(f"   类型: {ann.announcement_type_raw}")
                print()
            return announcements
        else:
            print("\n⚠️  未采集到公告，将使用Mock数据\n")
            return None

    except Exception as e:
        print(f"\n❌ API调用失败: {e}")
        print("⚠️  将使用Mock数据\n")
        return None


def main():
    # 先尝试真实API
    announcements = test_real_api()

    # 如果失败，使用mock数据
    if not announcements:
        announcements = test_with_mock_data()
        print(f"✅ 使用 {len(announcements)} 条Mock数据")

    # 测试pipeline
    print("\n" + "=" * 80)
    print("测试Pipeline处理")
    print("=" * 80)

    from fund_quant.pipelines.announcement_pipeline import SingleAnnouncementPipeline

    pipeline = SingleAnnouncementPipeline()

    for ann in announcements[:3]:
        print(f"\n处理: {ann.title[:50]}...")
        result = pipeline.process(ann, "test_batch")

        print(f"  股票: [{result.stock_code}] {result.stock_name}")
        print(f"  类型: {result.announcement_type}")
        print(f"  Action: {result.action}")
        print(f"  需AI: {result.need_ai}, 需PDF: {result.need_pdf}")
        print(f"  预评分: {result.pre_score}")
        print(f"  状态: {result.processing_status}")

    print("\n✅ Pipeline测试完成")


if __name__ == '__main__':
    main()
