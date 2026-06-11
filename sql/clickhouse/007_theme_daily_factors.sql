-- 主题日度因子表
-- 用于存储每个主题每日的强度因子，包括收益率、Alpha、成交额倍数、均线等

CREATE TABLE IF NOT EXISTS theme_daily_factors (
    trade_date Date COMMENT '交易日期',
    theme_id String COMMENT '主题ID',
    theme_name String COMMENT '主题名称',

    index_symbol String COMMENT '主题指数代码',
    etf_symbol String COMMENT '主题ETF代码',

    index_close Float64 COMMENT '指数收盘价',
    etf_close Float64 COMMENT 'ETF收盘价',

    -- 收益率（基于指数）
    ret_1d Float64 COMMENT '1日收益率(%)',
    ret_3d Float64 COMMENT '3日收益率(%)',
    ret_5d Float64 COMMENT '5日收益率(%)',
    ret_20d Float64 COMMENT '20日收益率(%)',
    ret_60d Float64 COMMENT '60日收益率(%)',

    -- 基准收益率（沪深300）
    hs300_ret_5d Float64 COMMENT '沪深300 5日收益率(%)',
    hs300_ret_20d Float64 COMMENT '沪深300 20日收益率(%)',
    hs300_ret_60d Float64 COMMENT '沪深300 60日收益率(%)',

    -- Alpha（超额收益）
    alpha_5d Float64 COMMENT '5日Alpha(%)',
    alpha_20d Float64 COMMENT '20日Alpha(%)',
    alpha_60d Float64 COMMENT '60日Alpha(%)',

    -- 成交额指标（基于ETF）
    etf_amount Float64 COMMENT 'ETF当日成交额(元)',
    amount_ma5 Float64 COMMENT 'ETF 5日平均成交额(元)',
    amount_ma20 Float64 COMMENT 'ETF 20日平均成交额(元)',
    amount_ratio_1d Float64 COMMENT '成交额倍数(当日/20日均)',
    amount_ratio_5d Float64 COMMENT '成交额倍数(5日均/20日均)',

    -- 指数均线
    index_ma5 Float64 COMMENT '指数MA5',
    index_ma10 Float64 COMMENT '指数MA10',
    index_ma20 Float64 COMMENT '指数MA20',
    index_ma30 Float64 COMMENT '指数MA30',
    index_ma60 Float64 COMMENT '指数MA60',
    index_ma250 Float64 COMMENT '指数MA250',

    -- 趋势状态
    above_ma20 UInt8 COMMENT '价格是否在MA20上方(0/1)',
    above_ma60 UInt8 COMMENT '价格是否在MA60上方(0/1)',
    ma20_gt_ma60 UInt8 COMMENT 'MA20是否在MA60上方(0/1)',
    ma5_gt_ma20 UInt8 COMMENT 'MA5是否在MA20上方(0/1)',
    trend_score UInt8 COMMENT '趋势得分(0-4)',

    created_at DateTime DEFAULT now() COMMENT '创建时间'
)
ENGINE = ReplacingMergeTree(created_at)
ORDER BY (trade_date, theme_id)
COMMENT '主题日度因子表';
