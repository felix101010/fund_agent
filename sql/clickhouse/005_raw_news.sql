-- 原始新闻表
-- 存储从各个渠道采集的原始新闻数据
CREATE TABLE IF NOT EXISTS raw_news
(
    id String COMMENT '新闻ID（UUID或source_id）',
    source String COMMENT '数据源: cls/cninfo/reuters/reddit/twitter',
    source_type String COMMENT '源类型: news/filing/social/rss',
    title String COMMENT '标题',
    summary Nullable(String) COMMENT '摘要',
    content Nullable(String) COMMENT '正文内容',
    url String COMMENT '原文链接',
    url_hash String COMMENT 'URL哈希（用于去重）',
    content_hash String COMMENT '内容哈希（用于去重）',
    dedup_key String COMMENT '去重键（source + url_hash）',
    published_at DateTime COMMENT '新闻发布时间（原始时间）',
    collected_at DateTime COMMENT '系统采集时间（重要：回测用此时间）',
    processed_at Nullable(DateTime) COMMENT 'LLM处理时间',
    language String DEFAULT 'zh' COMMENT '语言: zh/en',
    raw_json String COMMENT '原始JSON数据',
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    updated_at DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(published_at)
ORDER BY (source, published_at, id)
SETTINGS index_granularity = 8192
COMMENT '原始新闻表';

-- 索引优化
ALTER TABLE raw_news ADD INDEX idx_source source TYPE bloom_filter GRANULARITY 1;
ALTER TABLE raw_news ADD INDEX idx_title title TYPE tokenbf_v1(30720, 2, 0) GRANULARITY 1;
ALTER TABLE raw_news ADD INDEX idx_dedup_key dedup_key TYPE bloom_filter GRANULARITY 1;
ALTER TABLE raw_news ADD INDEX idx_url_hash url_hash TYPE bloom_filter GRANULARITY 1;
ALTER TABLE raw_news ADD INDEX idx_content_hash content_hash TYPE bloom_filter GRANULARITY 1;

-- 常用查询示例
-- 查询最近的新闻
-- SELECT id, source, title, published_at, collected_at FROM raw_news ORDER BY collected_at DESC LIMIT 20;

-- 查询特定来源的新闻
-- SELECT title, published_at, url FROM raw_news WHERE source = 'cls' ORDER BY published_at DESC LIMIT 10;

-- 查询未处理的新闻（待LLM处理）
-- SELECT id, source, title FROM raw_news WHERE processed_at IS NULL ORDER BY collected_at DESC LIMIT 100;

-- 去重检查
-- SELECT dedup_key, count() as cnt FROM raw_news GROUP BY dedup_key HAVING cnt > 1;

-- 查询某个时间段的新闻数量统计
-- SELECT source, toDate(published_at) as date, count() as cnt FROM raw_news WHERE published_at >= '2026-05-01' GROUP BY source, date ORDER BY date DESC, cnt DESC;

-- 重要：回测时使用 collected_at 而不是 published_at
-- SELECT id, title, collected_at FROM raw_news WHERE collected_at BETWEEN '2026-05-01 09:30:00' AND '2026-05-01 15:00:00' ORDER BY collected_at;
