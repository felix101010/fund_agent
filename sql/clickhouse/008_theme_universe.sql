-- 主题知识库表
-- 存储所有主题的定义和属性

CREATE TABLE IF NOT EXISTS quant.theme_universe
(
    theme_id String COMMENT '主题ID',
    theme_name String COMMENT '主题名称',
    theme_category String COMMENT '主题分类: tech/energy/healthcare/finance/consumer/defense/value',

    -- 主题属性
    volatility_level String COMMENT '波动性: high/medium/low',
    liquidity_level String COMMENT '流动性: high/medium/low',
    policy_sensitive UInt8 COMMENT '是否政策敏感: 1=是 0=否',
    description String COMMENT '主题描述',

    -- 新闻映射
    keywords Array(String) COMMENT '关键词列表',
    news_sources Array(String) COMMENT '新闻源优先级',

    -- 海外对标
    overseas_indices Array(String) COMMENT '海外对标指数',

    -- 元数据
    status String COMMENT '状态: active/inactive',
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY theme_id
COMMENT '主题知识库表';
