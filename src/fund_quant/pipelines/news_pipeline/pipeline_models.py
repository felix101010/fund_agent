"""
Pipeline 数据模型
定义新闻处理流程中的数据结构
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class NewsProcessResult:
    """单条新闻处理结果"""
    # 基础信息
    batch_id: str
    run_id: str
    news_id: str
    source: str
    title: str
    content: str
    publish_time: datetime
    url: str

    # 新闻源角色
    source_role: str = ""  # 例如：a_share_catalyst/market_context/macro_event

    # 去重标记
    is_new: bool = False  # 是否为新增新闻

    # 处理结果
    filter_result: Any = None  # SimpleRuleFilter结果
    unknown_refine_result: Any = None  # UnknownDecisionFilter结果
    need_ai: bool = False
    ai_raw_output: str = ""
    final_event: Any = None  # AIEventResult

    # 错误和校验
    validation_errors: list = field(default_factory=list)
    postprocess_notes: list = field(default_factory=list)
    error_tags: list = field(default_factory=list)
    used_fallback: bool = False

    # 处理状态
    processing_status: str = "pending"  # pending/success/failed/skipped
    processing_error: str = ""
    ai_failed: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BatchProcessResult:
    """批次处理结果"""
    batch_id: str
    run_id: str

    # 统计信息
    total_fetched: int = 0
    new_count: int = 0
    duplicated_count: int = 0
    processed_count: int = 0
    skipped_count: int = 0
    ai_success: int = 0
    ai_failed: int = 0
    fallback_count: int = 0

    # 详细结果
    results: list = field(default_factory=list)  # List[NewsProcessResult]
    stats: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DaemonRunResult:
    """Daemon单轮运行结果"""
    daemon_start_time: datetime
    run_id: str
    batch_id: str
    loop_index: int
    status: str  # success/failed/interrupted
    sleep_seconds: int
    batch_result: Optional[BatchProcessResult] = None
    error: str = ""


__all__ = ['NewsProcessResult', 'BatchProcessResult', 'DaemonRunResult']
