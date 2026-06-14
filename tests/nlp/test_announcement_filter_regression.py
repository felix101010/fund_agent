"""
公告过滤器回归测试
验证优化后的分类规则是否正确处理真实样本中的误判问题
"""
import pytest
from fund_quant.data_sources.announcements.announcement_models import RawAnnouncement
from fund_quant.nlp.announcements.announcement_filter import AnnouncementFilter
from datetime import datetime


class TestAnnouncementFilterRegression:
    """公告过滤器回归测试"""

    def setup_method(self):
        """初始化"""
        self.filter = AnnouncementFilter()

    def test_governance_policy_external_investment(self):
        """测试1：对外投资管理制度应archive，不应analyze"""
        announcement = RawAnnouncement(
            announcement_id="test_001",
            title="对外投资管理制度（2026年修订）",
            announcement_type_raw="制度修订",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "governance_policy_revision"
        assert result.action == "archive"
        assert result.need_ai == False
        assert result.need_pdf == False
        assert result.pre_score <= 10

    def test_governance_policy_external_guarantee(self):
        """测试2：对外担保管理制度应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_002",
            title="对外担保管理制度（2026年修订）",
            announcement_type_raw="制度修订",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "governance_policy_revision"
        assert result.action == "archive"
        assert result.need_ai == False
        assert result.pre_score <= 10

    def test_governance_policy_info_disclosure(self):
        """测试3：信息披露管理制度应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_003",
            title="信息披露管理制度（2026年修订）",
            announcement_type_raw="制度修订",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "governance_policy_revision"
        assert result.action == "archive"
        assert result.pre_score <= 10

    def test_board_resolution_with_number(self):
        """测试4：第七届董事会第二次会议决议公告应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_004",
            title="第七届董事会第二次会议决议公告",
            announcement_type_raw="董事会决议",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "board_resolution"
        assert result.action == "archive"
        assert result.need_ai == False
        assert result.pre_score <= 20

    def test_shareholder_meeting_notice(self):
        """测试5：召开股东会通知应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_005",
            title="关于召开2026年第三次临时股东会的通知",
            announcement_type_raw="股东会通知",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "shareholder_meeting_notice"
        assert result.action == "archive"
        assert result.pre_score <= 10

    def test_shareholder_change_5_percent(self):
        """测试6：持股5%以上股东权益变动应watch"""
        announcement = RawAnnouncement(
            announcement_id="test_006",
            title="关于持股5%以上股东权益变动触及1%刻度的提示性公告",
            announcement_type_raw="权益变动",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "shareholder_change"
        assert result.action == "watch"
        assert result.need_ai == False
        assert 35 <= result.pre_score <= 45

    def test_project_expansion_progress(self):
        """测试7：采选扩建项目进展应analyze"""
        announcement = RawAnnouncement(
            announcement_id="test_007",
            title="关于控股子公司赤峰中色白音诺尔矿业有限公司投资165万吨年铅锌矿采选扩建项目的进展公告",
            announcement_type_raw="项目进展",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "project_expansion_progress"
        assert result.action == "analyze"
        assert result.need_ai == True
        assert result.need_pdf == True
        assert result.pre_score >= 70

    def test_safety_accident(self):
        """测试8：安全事故应risk_review"""
        announcement = RawAnnouncement(
            announcement_id="test_008",
            title="关于公司发生安全事故的公告",
            announcement_type_raw="其他公告",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "safety_accident"
        assert result.action == "risk_review"
        assert result.need_ai == True
        assert result.need_pdf == True
        assert result.pre_score >= 75

    def test_pharma_regulatory_eu_gmp(self):
        """测试9：EU GMP检查应analyze/watch"""
        announcement = RawAnnouncement(
            announcement_id="test_009",
            title="关于永和工厂EU GMP检查情况的公告",
            announcement_type_raw="其他公告",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "pharma_regulatory_progress"
        assert result.action in ["analyze", "watch"]
        assert result.need_ai == True
        assert result.need_pdf == True
        assert result.pre_score >= 65

    def test_pharma_regulatory_nda(self):
        """测试10：药品上市申请获得受理应analyze"""
        announcement = RawAnnouncement(
            announcement_id="test_010",
            title="自愿披露关于iza-bren（EGFR×HER3双抗ADC）用于治疗局部晚期或转移性三阴乳腺癌的药品上市申请获得受理的公告",
            announcement_type_raw="自愿披露",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "pharma_regulatory_progress"
        assert result.action == "analyze"
        assert result.need_ai == True
        assert result.need_pdf == True
        assert result.pre_score >= 75

    def test_fundraising_project_change(self):
        """测试11：终止募投项目应risk_review/watch"""
        announcement = RawAnnouncement(
            announcement_id="test_011",
            title="关于终止部分募集资金投资项目的公告",
            announcement_type_raw="募集资金",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "fundraising_project_change"
        assert result.action in ["risk_review", "watch"]
        assert result.need_ai == True
        assert result.need_pdf == True
        assert result.pre_score >= 60

    def test_bond_fundraising_policy(self):
        """测试12：债券募集资金管理制度应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_012",
            title="公司债券募集资金管理制度",
            announcement_type_raw="制度",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "governance_policy_revision"
        assert result.action == "archive"
        assert result.pre_score <= 10

    def test_external_guarantee_real(self):
        """测试13：真实对外担保公告应watch/risk_review"""
        announcement = RawAnnouncement(
            announcement_id="test_013",
            title="对外担保公告",
            announcement_type_raw="对外担保",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "external_guarantee"
        assert result.action in ["watch", "risk_review"]
        assert result.need_pdf == True
        assert result.pre_score >= 50

    def test_asset_transfer(self):
        """测试14：股权转让应watch/analyze"""
        announcement = RawAnnouncement(
            announcement_id="test_014",
            title="关于全资子公司股权转让完成的公告",
            announcement_type_raw="股权转让",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "asset_or_equity_transfer"
        assert result.action in ["watch", "analyze"]
        assert result.need_ai == True
        assert result.need_pdf == True
        assert result.pre_score >= 55

    def test_bond_risk_notice(self):
        """测试15：可转债投资者适当性提示应archive/watch"""
        announcement = RawAnnouncement(
            announcement_id="test_015",
            title="关于可转债投资者适当性要求的风险提示性公告",
            announcement_type_raw="风险提示",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        # 新规则会归为convertible_bond_routine_notice
        assert result.announcement_type in ["bond_or_cb_risk_notice", "convertible_bond_routine_notice"]
        assert result.action in ["archive", "watch"]
        assert result.need_ai == False
        assert result.need_pdf == False
        assert result.pre_score <= 20

    def test_director_liability_insurance(self):
        """测试16：董事责任险应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_016",
            title="关于购买董事、高级管理人员责任险的公告",
            announcement_type_raw="其他公告",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "director_liability_insurance"
        assert result.action == "archive"
        assert result.need_ai == False
        assert result.need_pdf == False
        assert result.pre_score <= 10

    def test_compensation_policy(self):
        """测试17：薪酬方案应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_017",
            title="关于2026年度董事、高级管理人员薪酬方案的公告",
            announcement_type_raw="董事会决议",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "compensation_policy"
        assert result.action == "archive"
        assert result.need_ai == False
        assert result.pre_score <= 10

    def test_audit_institution_change(self):
        """测试18：聘请审计机构应archive/watch"""
        announcement = RawAnnouncement(
            announcement_id="test_018",
            title="关于聘请2026年度审计机构的公告",
            announcement_type_raw="其他公告",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "audit_institution_change"
        assert result.action in ["archive", "watch"]
        assert result.need_ai == False
        assert result.pre_score <= 20

    def test_director_candidate_nomination(self):
        """测试19：提名董事候选人应archive/watch"""
        announcement = RawAnnouncement(
            announcement_id="test_019",
            title="关于提名非独立董事候选人的公告",
            announcement_type_raw="董事会决议",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "director_candidate_nomination"
        assert result.action in ["archive", "watch"]
        assert result.need_ai == False
        assert result.pre_score <= 20

    def test_board_resolution_with_session_number(self):
        """测试20：带届次会议号的董事会决议应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_020",
            title="第五届董事会2026年第五次会议决议的公告",
            announcement_type_raw="董事会决议",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "board_resolution"
        assert result.action == "archive"
        assert result.pre_score <= 15

    def test_regulatory_clean_record(self):
        """测试21：无监管处罚记录声明应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_021",
            title="关于最近五年未被证券监管部门和证券交易所采取监管措施或处罚的公告",
            announcement_type_raw="其他公告",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "regulatory_clean_record"
        assert result.action == "archive"
        assert result.need_ai == False
        assert result.need_pdf == False
        assert result.pre_score <= 10

    def test_equity_incentive_adjustment(self):
        """测试22：股权激励注销不应识别为普通回购"""
        announcement = RawAnnouncement(
            announcement_id="test_022",
            title="关于注销部分股票期权与回购注销部分限制性股票的公告",
            announcement_type_raw="股权激励",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "equity_incentive_adjustment"
        assert result.action in ["archive", "watch"]
        assert result.need_ai == False
        assert result.need_pdf == False
        assert result.pre_score <= 30

    def test_dividend_implementation(self):
        """测试23：权益分派实施应archive"""
        announcement = RawAnnouncement(
            announcement_id="test_023",
            title="2026年权益分派实施公告",
            announcement_type_raw="分红派息",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "dividend_implementation"
        assert result.action == "archive"
        assert result.need_ai == False
        assert result.pre_score <= 15

    def test_trading_status_notice(self):
        """测试24：复牌提示应watch"""
        announcement = RawAnnouncement(
            announcement_id="test_024",
            title="关于公司股票复牌的提示性公告",
            announcement_type_raw="其他公告",
            publish_time=datetime.now()
        )

        result = self.filter.filter(announcement)

        assert result.announcement_type == "trading_status_notice"
        assert result.action in ["watch", "archive"]
        assert result.need_ai == False
        assert 20 <= result.pre_score <= 35


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
