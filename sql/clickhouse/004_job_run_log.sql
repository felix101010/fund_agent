-- 任务运行日志表
-- 记录每次数据采集任务的执行情况
CREATE TABLE IF NOT EXISTS job_run_log
(
    job_id String COMMENT '任务ID（UUID）',
    job_name String COMMENT '任务名称: collect_etf_symbols/collect_daily_bars等',
    source_name String COMMENT '数据源名称',
    start_time DateTime COMMENT '开始时间',
    end_time Nullable(DateTime) COMMENT '结束时间',
    status String COMMENT '状态: running/success/failed/partial',
    rows_read UInt64 DEFAULT 0 COMMENT '读取行数',
    rows_written UInt64 DEFAULT 0 COMMENT '写入行数',
    rows_failed UInt64 DEFAULT 0 COMMENT '失败行数',
    error_message Nullable(String) COMMENT '错误信息',
    params String DEFAULT '{}' COMMENT '任务参数(JSON)',
    metadata String DEFAULT '{}' COMMENT '额外元数据(JSON)',
    created_at DateTime DEFAULT now() COMMENT '创建时间'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (job_name, start_time, job_id)
SETTINGS index_granularity = 8192
COMMENT '任务运行日志表';

-- 索引优化
ALTER TABLE job_run_log ADD INDEX idx_status status TYPE bloom_filter GRANULARITY 1;
ALTER TABLE job_run_log ADD INDEX idx_source source_name TYPE bloom_filter GRANULARITY 1;

-- 常用查询示例
-- 查询最近的任务执行情况
-- SELECT job_name, start_time, end_time, status, rows_written FROM job_run_log ORDER BY start_time DESC LIMIT 20;

-- 查询失败的任务
-- SELECT job_name, start_time, error_message FROM job_run_log WHERE status = 'failed' ORDER BY start_time DESC LIMIT 10;

-- 查询某个任务的历史执行情况
-- SELECT start_time, status, rows_written, dateDiff('second', start_time, end_time) as duration_sec FROM job_run_log WHERE job_name = 'collect_daily_bars' ORDER BY start_time DESC LIMIT 20;

-- 统计任务成功率
-- SELECT job_name, countIf(status = 'success') as success_count, countIf(status = 'failed') as failed_count, count() as total FROM job_run_log WHERE start_time >= now() - INTERVAL 7 DAY GROUP BY job_name;
