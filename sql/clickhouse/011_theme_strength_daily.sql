-- 主题强度日度表
-- 存储每个主题每日的综合强度评分

CREATE TABLE IF NOT EXISTS quant.theme_strength_daily
(
    theme_id String COMMENT '主题ID',
    trade_date Date COMMENT '交易日期',

    -- 价格强度
    index_return Float32 COMMENT '主题指数收益率',
    index_volume_ratio Float32 COMMENT '成交量比率（相对5日均值）',
    index_amount_ratio Float32 COMMENT '成交额比率（相对5日均值）',

    -- 相对强度
    vs_market_alpha Float32 COMMENT '相对市场Alpha（vs沪深300）',
    vs_sector_alpha Nullable(Float32) COMMENT '相对行业Alpha',
    momentum_5d Float32 COMMENT '5日动量',
    momentum_20d Float32 COMMENT '20日动量',

    -- 技术指标
    rsi_14 Nullable(Float32) COMMENT 'RSI(14)',
    macd Nullable(Float32) COMMENT 'MACD',
    bollinger_position Nullable(Float32) COMMENT '布林带位置 0-1',

    -- 新闻强度
    news_count Int32 DEFAULT 0 COMMENT '新闻数量',
    news_sentiment Nullable(Float32) COMMENT '新闻情绪 -1到1',
    news_heat Nullable(Float32) COMMENT '新闻热度',

    -- 综合评分
    price_strength_score Float32 COMMENT '价格强度评分 0-100',
    volume_strength_score Float32 COMMENT '成交量强度评分 0-100',
    news_strength_score Nullable(Float32) COMMENT '新闻强度评分 0-100',

    strength_score Float32 COMMENT '综合强度评分 0-100',
    rank Int32 COMMENT '当日排名',

    -- 元数据
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, theme_id)
COMMENT '主题强度日度表';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_theme_id ON quant.theme_strength_daily (theme_id) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_strength_score ON quant.theme_strength_daily (strength_score) TYPE minmax GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_rank ON quant.theme_strength_daily (rank) TYPE minmax GRANULARITY 1;
