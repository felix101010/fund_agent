-- 证券主数据表
-- 存储 ETF、股票、指数的基础信息
CREATE TABLE IF NOT EXISTS symbol_master
(
    symbol String COMMENT '证券代码，如 159272.SZ',
    name String COMMENT '证券名称',
    asset_type String COMMENT '资产类型: ETF/STOCK/INDEX',
    exchange String COMMENT '交易所: SH/SZ',
    list_date Date COMMENT '上市日期',
    delist_date Nullable(Date) COMMENT '退市日期',
    status String COMMENT '状态: active/delisted/suspended',
    fund_type Nullable(String) COMMENT 'ETF类型: 股票型/债券型/货币型等',
    source String COMMENT '数据源: tushare',
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (asset_type, symbol)
SETTINGS index_granularity = 8192
COMMENT '证券主数据表';

-- 索引优化
ALTER TABLE symbol_master ADD INDEX idx_name name TYPE tokenbf_v1(30720, 2, 0) GRANULARITY 1;
ALTER TABLE symbol_master ADD INDEX idx_status status TYPE bloom_filter GRANULARITY 1;

-- 常用查询示例
-- 查询所有活跃的ETF
-- SELECT symbol, name, list_date FROM symbol_master WHERE asset_type = 'ETF' AND status = 'active' ORDER BY list_date DESC;

-- 查询特定交易所的证券
-- SELECT symbol, name, asset_type FROM symbol_master WHERE exchange = 'SZ' AND status = 'active';
