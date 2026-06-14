"""
测试 Daemon 基础功能
"""
import pytest
from datetime import datetime
from pathlib import Path

from fund_quant.pipelines.news_pipeline.cls_batch_pipeline import ClsBatchPipeline
from fund_quant.pipelines.news_pipeline.pipeline_models import BatchProcessResult


def test_batch_pipeline_run_once():
    """测试批次处理能正常运行一轮"""
    pipeline = ClsBatchPipeline(
        limit=5,
        only_new=True,
        verbose=False,
        save_raw=False,
        save_events=False,
        save_jsonl=False,
        save_csv=False,
        output_dir="data/review/test_outputs"
    )

    result = pipeline.run_once(run_id="test_run", loop_index=1)

    assert isinstance(result, BatchProcessResult)
    assert result.batch_id.startswith("cls_")
    assert result.total_fetched >= 0

    print(f"\n✅ 批次处理测试通过")
    print(f"  抓取: {result.total_fetched}")
    print(f"  新增: {result.new_count}")
    print(f"  重复: {result.duplicated_count}")


def test_dedup_manager():
    """测试去重管理器"""
    from fund_quant.data.storage.news_dedup_manager import NewsDedupManager

    # 使用测试文件
    test_file = "data/review/test_seen_ids.txt"
    dedup = NewsDedupManager(seen_file_path=test_file)

    # 测试标记和查重
    test_id = "test_news_123"
    dedup.mark_as_seen(test_id)

    assert dedup.is_duplicate(test_id) is True
    assert dedup.is_duplicate("not_exist_id") is False

    # 清理
    Path(test_file).unlink(missing_ok=True)

    print(f"\n✅ 去重管理器测试通过")


def test_error_classifier():
    """测试错误分类器"""
    from fund_quant.research.news_review.error_classifier import ErrorClassifier
    from fund_quant.pipelines.news_pipeline.pipeline_models import NewsProcessResult
    from fund_quant.nlp.news_ai.ai_event_models import AIEventResult

    # 创建测试结果
    process_result = NewsProcessResult(
        batch_id="test_batch",
        run_id="test_run",
        news_id="test_001",
        source="cls",
        title="光波导投产",
        content="全球首条体全息光波导自动化产线投产",
        publish_time=datetime.now(),
        url="",
        is_new=True,
        used_fallback=True
    )

    # 添加AI结果
    process_result.final_event = AIEventResult(
        news_id="test_001",
        is_market_relevant=True,
        event_type="mass_production",
        theme="消费电子",
        sub_themes=[],
        related_stocks=[],
        sentiment="positive",
        event_level="A",
        novelty_type="new_theme",
        summary="",
        confidence=0.8,
        final_score=85,
        trade_priority="high",
        primary_theme_id="xr_optics",
        primary_theme_name="XR光学"
    )

    # 分类
    classifier = ErrorClassifier()
    tags = classifier.classify(process_result)

    assert "fallback_used" in tags
    assert "high_score_without_stock" in tags

    print(f"\n✅ 错误分类器测试通过")
    print(f"  错误标签: {tags}")


if __name__ == "__main__":
    test_batch_pipeline_run_once()
    test_dedup_manager()
    test_error_classifier()
    print(f"\n🎉 所有测试通过！")
