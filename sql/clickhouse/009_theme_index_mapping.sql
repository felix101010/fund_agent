-- 主题-指数映射表
-- 定义每个主题对应的分析指数

CREATE TABLE IF NOT EXISTS quant.theme_index_mapping
(
    theme_id String COMMENT '主题ID',
    index_symbol String COMMENT '指数代码',
    index_name String COMMENT '指数名称',

    -- 指数属性
    role String COMMENT '角色: primary/secondary/benchmark',
    weight Float32 COMMENT '权重（用于多指数加权）',
    description String COMMENT '指数描述',

    -- 跟踪质量
    constituent_count Nullable(Int32) COMMENT '成分股数量',
    concentration_top10 Nullable(Float32) COMMENT '前10大权重占比',

    -- 元数据
    list_date Nullable(Date) COMMENT '发布日期',
    status String DEFAULT 'active' COMMENT '状态: active/inactive',
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (theme_id, index_symbol)
COMMENT '主题-指数映射表';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_theme_id ON quant.theme_index_mapping (theme_id) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_role ON quant.theme_index_mapping (role) TYPE set(0) GRANULARITY 1;
