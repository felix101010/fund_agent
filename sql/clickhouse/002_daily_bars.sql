-- 统一日线行情表
-- 存储 ETF、股票、指数的日线数据
CREATE TABLE IF NOT EXISTS daily_bars
(
    symbol String COMMENT '证券代码',
    asset_type String COMMENT '资产类型: ETF/STOCK/INDEX',
    trade_date Date COMMENT '交易日期',
    open Decimal(10, 3) COMMENT '开盘价',
    high Decimal(10, 3) COMMENT '最高价',
    low Decimal(10, 3) COMMENT '最低价',
    close Decimal(10, 3) COMMENT '收盘价',
    pre_close Decimal(10, 3) COMMENT '昨收价',
    change Decimal(10, 3) COMMENT '涨跌额',
    pct_chg Decimal(10, 3) COMMENT '涨跌幅(%)',
    volume Decimal(20, 2) COMMENT '成交量(手)',
    amount Decimal(20, 2) COMMENT '成交额(千元)',
    adj_factor Nullable(Decimal(10, 6)) COMMENT '复权因子',
    adj_type String DEFAULT 'none' COMMENT '复权类型: none/qfq/hfq',
    turnover_rate Nullable(Decimal(10, 3)) COMMENT '换手率(%)',
    source String COMMENT '数据源: tushare',
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (symbol, asset_type, trade_date)
SETTINGS index_granularity = 8192
COMMENT '统一日线行情表';

-- 索引优化
ALTER TABLE daily_bars ADD INDEX idx_asset_type asset_type TYPE bloom_filter GRANULARITY 1;

-- 常用查询示例
-- 查询某个ETF的历史行情
-- SELECT trade_date, open, high, low, close, volume, amount FROM daily_bars WHERE symbol = '159272.SZ' AND asset_type = 'ETF' ORDER BY trade_date DESC LIMIT 30;

-- 查询某日所有ETF的涨幅排名
-- SELECT symbol, close, pct_chg, amount FROM daily_bars WHERE asset_type = 'ETF' AND trade_date = '2026-05-30' ORDER BY pct_chg DESC LIMIT 20;

-- 查询某个时间段的行情
-- SELECT trade_date, close, volume FROM daily_bars WHERE symbol = '159272.SZ' AND trade_date BETWEEN '2025-01-01' AND '2026-05-30' ORDER BY trade_date;

-- 数据质量检查：查找异常数据
-- SELECT symbol, trade_date, high, low FROM daily_bars WHERE high < low LIMIT 10;
-- SELECT symbol, trade_date, close FROM daily_bars WHERE close <= 0 LIMIT 10;
