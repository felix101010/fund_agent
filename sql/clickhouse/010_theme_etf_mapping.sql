-- 主题-ETF映射表
-- 定义每个主题对应的交易工具（ETF）

CREATE TABLE IF NOT EXISTS quant.theme_etf_mapping
(
    theme_id String COMMENT '主题ID',
    etf_symbol String COMMENT 'ETF代码',
    etf_name String COMMENT 'ETF名称',

    -- ETF属性
    role String COMMENT '角色: primary/backup/alternative',
    tracking_index String COMMENT '跟踪指数',
    description String COMMENT 'ETF描述',

    -- 交易属性
    avg_daily_volume Nullable(Decimal(20, 2)) COMMENT '日均成交量',
    avg_daily_amount Nullable(Decimal(20, 2)) COMMENT '日均成交额',
    management_fee Nullable(Float32) COMMENT '管理费率',
    tracking_error Nullable(Float32) COMMENT '跟踪误差',

    -- 流动性评级
    liquidity_score Nullable(Float32) COMMENT '流动性评分 0-100',
    execution_quality String COMMENT '执行质量: excellent/good/fair/poor',

    -- 元数据
    list_date Nullable(Date) COMMENT '上市日期',
    fund_size Nullable(Decimal(20, 2)) COMMENT '基金规模（亿元）',
    status String DEFAULT 'active' COMMENT '状态: active/inactive',
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (theme_id, etf_symbol)
COMMENT '主题-ETF映射表';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_theme_id ON quant.theme_etf_mapping (theme_id) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_role ON quant.theme_etf_mapping (role) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_liquidity ON quant.theme_etf_mapping (liquidity_score) TYPE minmax GRANULARITY 1;
