-- 采集状态表
-- 记录每个证券的数据采集状态，支持断点续采

CREATE TABLE IF NOT EXISTS quant.collection_status
(
    symbol String COMMENT '证券代码',
    asset_type String COMMENT '资产类型: ETF/INDEX/STOCK',
    priority String COMMENT '优先级: P0/P1/P2',
    theme String COMMENT '所属主题',

    -- 采集状态
    last_collected_date Date COMMENT '最后采集日期',
    total_bars Int32 DEFAULT 0 COMMENT '总行情条数',
    first_trade_date Date COMMENT '首个交易日',
    latest_trade_date Date COMMENT '最新交易日',

    -- 数据质量
    missing_dates Int32 DEFAULT 0 COMMENT '缺失交易日数量',
    quality_score Float32 DEFAULT 0.0 COMMENT '数据质量评分 0-1',
    last_quality_check DateTime COMMENT '最后质量检查时间',

    -- 采集统计
    collection_count Int32 DEFAULT 0 COMMENT '采集次数',
    last_collection_time DateTime COMMENT '最后采集时间',
    last_collection_status String COMMENT '最后采集状态: success/failed/partial',
    last_error_message String COMMENT '最后错误信息',

    -- 元数据
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(last_collected_date)
ORDER BY (symbol, asset_type)
COMMENT '证券数据采集状态表';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_priority ON quant.collection_status (priority) TYPE minmax GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_theme ON quant.collection_status (theme) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_status ON quant.collection_status (last_collection_status) TYPE set(0) GRANULARITY 1;
