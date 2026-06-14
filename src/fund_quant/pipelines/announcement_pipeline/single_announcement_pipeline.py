"""
单条公告处理流程（集成PDF下载和文本提取）
"""
from typing import Any, Optional
from fund_quant.nlp.announcements.announcement_filter import AnnouncementFilter
from fund_quant.nlp.announcements.company_theme_mapping import get_company_theme
from fund_quant.data_sources.announcements.cninfo_pdf_downloader import CninfoPdfDownloader
from fund_quant.nlp.announcements.announcement_pdf_text_extractor import AnnouncementPdfTextExtractor
from fund_quant.pipelines.announcement_pipeline.announcement_pipeline_models import AnnouncementProcessResult


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# 高价值PDF类型（需要下载和解析）
HIGH_VALUE_PDF_TYPES = {
    "project_expansion_progress",
    "safety_accident",
    "external_guarantee",
    "asset_or_equity_transfer",
    "pharma_regulatory_progress",
    "fundraising_project_change",
    "abnormal_trading",
    "major_contract",
    "bid_winning",
    "share_buyback",
    "shareholding_reduction",
    "regulatory_penalty",
}


class SingleAnnouncementPipeline:
    """
    单条公告处理流程

    流程：
    1. AnnouncementFilter过滤
    2. PDF下载和文本提取（如果need_pdf=True且属于高价值类型）
    3. 主题映射、评分、限分
    4. 返回AnnouncementProcessResult
    """

    def __init__(self, pdf_output_dir: str = "data/raw/cninfo_pdfs"):
        """初始化"""
        self.filter = AnnouncementFilter()
        self.pdf_downloader = CninfoPdfDownloader(output_dir=pdf_output_dir)
        self.pdf_extractor = AnnouncementPdfTextExtractor(max_pages=10)

    def should_parse_pdf(self, need_pdf: bool, pdf_url: str, announcement_type: str) -> bool:
        """
        判断是否应该解析PDF

        Args:
            need_pdf: 是否需要PDF
            pdf_url: PDF URL
            announcement_type: 公告类型

        Returns:
            bool
        """
        return (
            need_pdf is True
            and bool(pdf_url)
            and announcement_type in HIGH_VALUE_PDF_TYPES
        )

    def process(self, announcement: Any, batch_id: str) -> AnnouncementProcessResult:
        """
        处理单条公告

        Args:
            announcement: RawAnnouncement
            batch_id: 批次ID

        Returns:
            AnnouncementProcessResult
        """
        try:
            # 提取基本字段
            announcement_id = get_field(announcement, 'announcement_id', '')
            stock_code = get_field(announcement, 'stock_code', '')
            stock_name = get_field(announcement, 'stock_name', '')
            title = get_field(announcement, 'title', '')
            publish_time = get_field(announcement, 'publish_time')
            url = get_field(announcement, 'url', '')
            pdf_url = get_field(announcement, 'pdf_url', '')
            announcement_type_raw = get_field(announcement, 'announcement_type_raw', '')

            # 1. 过滤
            filter_result = self.filter.filter(announcement)

            # 2. 初始化结果
            result = AnnouncementProcessResult(
                batch_id=batch_id,
                announcement_id=announcement_id,
                stock_code=stock_code,
                stock_name=stock_name,
                title=title,
                publish_time=publish_time,
                url=url,
                pdf_url=pdf_url,
                announcement_type_raw=announcement_type_raw,
                announcement_type=filter_result.announcement_type,
                action=filter_result.action,
                need_ai=filter_result.need_ai,
                need_pdf=filter_result.need_pdf,
                pre_score=filter_result.pre_score,
                matched_keywords=filter_result.matched_keywords,
                reasons=filter_result.reasons
            )

            # 3. 验证股票信息
            if not stock_code or not stock_name:
                result.error_tags.append('stock_missing')
                result.validation_errors.append('股票代码或名称缺失')

            # 4. PDF下载和文本提取（新增）
            if self.should_parse_pdf(filter_result.need_pdf, pdf_url, filter_result.announcement_type):
                try:
                    # 设置为pending
                    result.pdf_download_status = "pending"
                    result.pdf_parse_status = "pending"

                    # 下载PDF
                    download_result = self.pdf_downloader.download(                                                                  
                        announcement_id=announcement_id,           
                        pdf_url=pdf_url,                                                                                             
                        publish_time=publish_time                                                             
                    )   

                    result.pdf_download_status = download_result['status']

                    if download_result['status'] == 'success':
                        result.pdf_local_path = download_result['local_path']

                        # 提取PDF文本
                        extract_result = self.pdf_extractor.extract(result.pdf_local_path)

                        result.pdf_parse_status = extract_result['status']

                        if extract_result['status'] == 'success':
                            result.pdf_parsed = True
                            result.pdf_text_length = extract_result['text_length']
                            result.pdf_text_preview = extract_result['text'][:1000]
                            result.pdf_extraction_method = extract_result['method']
                            result.postprocess_notes.append(f"PDF已解析（{extract_result['method']}），待后续正文事件抽取")
                        else:
                            result.pdf_parsed = False
                            result.pdf_parse_error = extract_result['error']
                            result.error_tags.append('pdf_parse_failed')
                    else:
                        # 下载失败
                        result.pdf_download_status = "failed"
                        result.pdf_parse_status = "failed"
                        result.pdf_parsed = False
                        result.pdf_local_path = ""
                        result.pdf_parse_error = download_result.get('error', '')
                        result.error_tags.append('pdf_download_failed')

                except Exception as e:
                    # PDF处理失败不中断pipeline
                    result.pdf_download_status = "failed"
                    result.pdf_parse_status = "failed"
                    result.pdf_parsed = False
                    result.pdf_parse_error = f"PDF处理异常: {str(e)}"
                    result.error_tags.append('pdf_process_exception')
            else:
                # 不需要解析PDF - 统一设置not_required状态
                result.pdf_download_status = "not_required"
                result.pdf_parse_status = "not_required"
                result.pdf_parsed = False
                result.pdf_local_path = ""
                result.pdf_parse_error = ""
                # 不添加error_tags

            # 5. 如果need_ai=False，直接返回
            if not filter_result.need_ai:
                result.processing_status = 'success'
                result.final_event = {
                    'event_type': filter_result.announcement_type,
                    'related_stocks': [{'code': stock_code, 'name': stock_name}] if stock_code else [],
                    'final_score': filter_result.pre_score,
                    'trade_priority': self._map_priority(filter_result.pre_score),
                    'confidence': 0.5,
                    'signal_direction': 'neutral',
                    'risk_priority': 'none',
                    'risk_flags': [],
                    'primary_theme_id': None,
                    'primary_theme_name': None,
                    'secondary_theme_id': None,
                    'secondary_theme_name': None
                }
                return result

            # 6. TODO: AI抽取（当前阶段简化，只用title）
            if not result.pdf_parsed:
                result.postprocess_notes.append('当前阶段：标题级处理，未进行PDF全文解析')

            # 7. 构建事件（增加risk_priority、signal_direction、限分）
            signal_direction = "neutral"
            risk_priority = "none"
            final_score = filter_result.pre_score
            confidence = 0.6 if not result.pdf_parsed else 0.8
            risk_flags = []

            ann_type = filter_result.announcement_type

            # 根据announcement_type判断信号方向和风险优先级
            if ann_type == "safety_accident":
                signal_direction = "negative"
                risk_priority = "urgent"
                risk_flags = ["safety_accident", "production_disruption_risk"]
                if not result.pdf_parsed and filter_result.need_pdf:
                    result.postprocess_notes.append("安全事故标题级：保持风险评分但需PDF验证影响")

            elif ann_type == "abnormal_trading":
                signal_direction = "mixed"
                risk_priority = "high"
                risk_flags = ["abnormal_trading"]
                if not result.pdf_parsed and filter_result.need_pdf:
                    final_score = min(final_score, 75)
                    result.pdf_unparsed_score_cap = 75
                    result.postprocess_notes.append(f"标题级未解析PDF，评分上限{result.pdf_unparsed_score_cap}")

            elif ann_type in ["fundraising_project_change"]:
                signal_direction = "negative" if "终止" in title else "mixed"
                risk_priority = "high"
                if not result.pdf_parsed and filter_result.need_pdf:
                    final_score = min(final_score, 75)
                    result.pdf_unparsed_score_cap = 75
                    result.postprocess_notes.append(f"标题级未解析PDF，评分上限{result.pdf_unparsed_score_cap}")

            elif ann_type == "shareholding_reduction":
                signal_direction = "negative"
                risk_priority = "watch"

            elif ann_type == "project_expansion_progress":
                signal_direction = "positive"
                risk_priority = "none"
                if not result.pdf_parsed and filter_result.need_pdf:
                    final_score = min(final_score, 75)
                    result.pdf_unparsed_score_cap = 75
                    result.postprocess_notes.append(f"标题级未解析PDF，评分上限{result.pdf_unparsed_score_cap}")

            elif ann_type == "pharma_regulatory_progress":
                signal_direction = "positive"
                risk_priority = "none"
                if not result.pdf_parsed and filter_result.need_pdf:
                    final_score = min(final_score, 75)
                    result.pdf_unparsed_score_cap = 75
                    result.postprocess_notes.append(f"标题级未解析PDF，评分上限{result.pdf_unparsed_score_cap}")

            elif ann_type == "external_guarantee":
                signal_direction = "mixed"
                risk_priority = "watch"
                risk_flags = ["guarantee_risk"]
                if not result.pdf_parsed and filter_result.need_pdf:
                    final_score = min(final_score, 65)
                    result.pdf_unparsed_score_cap = 65
                    result.postprocess_notes.append(f"标题级未解析PDF，评分上限{result.pdf_unparsed_score_cap}")

            elif ann_type == "asset_or_equity_transfer":
                signal_direction = "mixed"
                risk_priority = "watch"
                if not result.pdf_parsed and filter_result.need_pdf:
                    final_score = min(final_score, 70)
                    result.pdf_unparsed_score_cap = 70
                    result.postprocess_notes.append(f"标题级未解析PDF，评分上限{result.pdf_unparsed_score_cap}")

            # 8. 获取公司主题映射
            theme_info = get_company_theme(stock_code, title)
            primary_theme_id = theme_info.get('primary_theme_id')
            primary_theme_name = theme_info.get('primary_theme_name')
            secondary_theme_id = theme_info.get('secondary_theme_id')
            secondary_theme_name = theme_info.get('secondary_theme_name')

            # 特殊：阳谷华泰安全事故增加化工安全风险
            if ann_type == "safety_accident" and stock_code == "300121.SZ":
                if "chemical_safety_risk" not in risk_flags:
                    risk_flags.append("chemical_safety_risk")

            # 9. 计算trade_priority（安全事故不urgent）
            if ann_type == "safety_accident":
                trade_priority = "watch"
            else:
                trade_priority = self._map_priority(final_score)

            result.final_event = {
                'event_type': ann_type,
                'related_stocks': [{'code': stock_code, 'name': stock_name}] if stock_code else [],
                'final_score': final_score,
                'trade_priority': trade_priority,
                'confidence': confidence,
                'signal_direction': signal_direction,
                'risk_priority': risk_priority,
                'risk_flags': risk_flags,
                'primary_theme_id': primary_theme_id,
                'primary_theme_name': primary_theme_name,
                'secondary_theme_id': secondary_theme_id,
                'secondary_theme_name': secondary_theme_name
            }

            result.processing_status = 'success'
            return result

        except Exception as e:
            # 失败处理
            result.processing_status = 'failed'
            result.processing_error = str(e)
            return result

    def _map_priority(self, score: int) -> str:
        """映射优先级"""
        if score >= 85:
            return 'urgent'
        elif score >= 70:
            return 'high'
        elif score >= 50:
            return 'candidate'
        else:
            return 'watch'


__all__ = ['SingleAnnouncementPipeline']
