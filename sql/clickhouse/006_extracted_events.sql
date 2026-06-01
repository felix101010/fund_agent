-- 新闻事件抽取结果表
-- 存储从新闻中提取的结构化事件信息
CREATE TABLE IF NOT EXISTS extracted_events
(
    news_id String COMMENT '关联的新闻ID',
    event_type String COMMENT '事件类型: product_release/earnings/policy/price_move等',
    companies Array(String) COMMENT '相关公司列表',
    themes Array(String) COMMENT '相关主题列表',
    sentiment String COMMENT '情绪: positive/negative/neutral',
    importance_score UInt8 COMMENT '重要性评分 0-100',
    confidence Float32 COMMENT '置信度 0-1',
    a_share_mapping UInt8 COMMENT '是否有A股映射: 0/1',
    related_stocks Array(String) COMMENT '相关A股代码',
    related_etfs Array(String) COMMENT '相关ETF代码',
    catalyst_direction Nullable(String) COMMENT '催化方向: bullish/bearish/neutral',
    reason String COMMENT '判断理由',
    model_name String COMMENT '使用的模型名称（重要：可复现）',
    prompt_version String COMMENT '提示词版本（重要：可复现）',
    extracted_at DateTime DEFAULT now() COMMENT '提取时间',
    created_at DateTime DEFAULT now() COMMENT '创建时间'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(extracted_at)
ORDER BY (event_type, extracted_at, news_id)
SETTINGS index_granularity = 8192
COMMENT '新闻事件抽取结果表';

-- 索引优化
ALTER TABLE extracted_events ADD INDEX idx_event_type event_type TYPE bloom_filter GRANULARITY 1;
ALTER TABLE extracted_events ADD INDEX idx_sentiment sentiment TYPE bloom_filter GRANULARITY 1;
ALTER TABLE extracted_events ADD INDEX idx_a_share_mapping a_share_mapping TYPE bloom_filter GRANULARITY 1;
ALTER TABLE extracted_events ADD INDEX idx_model model_name TYPE bloom_filter GRANULARITY 1;

-- 常用查询示例
-- 查询最近的高重要性事件
-- SELECT e.event_type, e.companies, e.themes, e.sentiment, e.importance_score, n.title, n.published_at
-- FROM extracted_events e JOIN raw_news n ON e.news_id = n.id
-- WHERE e.extracted_at >= now() - INTERVAL 24 HOUR AND e.importance_score >= 70
-- ORDER BY e.importance_score DESC, n.published_at DESC LIMIT 20;

-- 查询特定公司的事件
-- SELECT e.event_type, e.sentiment, e.importance_score, n.title, n.published_at
-- FROM extracted_events e JOIN raw_news n ON e.news_id = n.id
-- WHERE has(e.companies, 'nvidia') AND n.published_at >= now() - INTERVAL 7 DAY
-- ORDER BY n.published_at DESC;

-- 查询A股相关事件统计
-- SELECT e.themes, e.related_etfs, e.sentiment, count() as cnt
-- FROM extracted_events e
-- WHERE e.a_share_mapping = 1 AND e.extracted_at >= now() - INTERVAL 7 DAY
-- GROUP BY e.themes, e.related_etfs, e.sentiment
-- ORDER BY cnt DESC;

-- 查询特定主题的事件
-- SELECT e.event_type, e.sentiment, e.importance_score, n.title
-- FROM extracted_events e JOIN raw_news n ON e.news_id = n.id
-- WHERE has(e.themes, 'AI芯片') AND e.extracted_at >= now() - INTERVAL 3 DAY
-- ORDER BY e.importance_score DESC;

-- 按模型版本统计（用于A/B测试）
-- SELECT model_name, prompt_version, count() as cnt, avg(confidence) as avg_conf
-- FROM extracted_events
-- WHERE extracted_at >= now() - INTERVAL 7 DAY
-- GROUP BY model_name, prompt_version
-- ORDER BY cnt DESC;
