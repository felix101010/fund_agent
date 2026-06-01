-- 数据源状态表
-- 追踪每个数据源的最新采集状态
CREATE TABLE IF NOT EXISTS source_status
(
    source_name String COMMENT '数据源名称: tushare_etf/tushare_stock/cls_news等',
    data_type String COMMENT '数据类型: symbols/daily_bars/news/events',
    last_success_time DateTime COMMENT '最后成功时间',
    last_trade_date Nullable(Date) COMMENT '最后交易日期（仅行情数据）',
    last_id Nullable(String) COMMENT '最后处理的ID（新闻等）',
    status String COMMENT '状态: success/failed/partial',
    error_message Nullable(String) COMMENT '错误信息',
    rows_processed UInt64 DEFAULT 0 COMMENT '处理行数',
    metadata String DEFAULT '{}' COMMENT '额外元数据(JSON)',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (source_name, data_type)
SETTINGS index_granularity = 8192
COMMENT '数据源状态表';

-- 常用查询示例
-- 查询所有数据源的最新状态
-- SELECT source_name, data_type, last_success_time, status FROM source_status ORDER BY last_success_time DESC;

-- 查询失败的数据源
-- SELECT source_name, data_type, error_message, updated_at FROM source_status WHERE status = 'failed';

-- 查询行情数据的最新日期
-- SELECT source_name, last_trade_date FROM source_status WHERE data_type = 'daily_bars' ORDER BY last_trade_date DESC;
