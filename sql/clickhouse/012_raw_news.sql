-- 原始新闻表

CREATE TABLE IF NOT EXISTS raw_news (
    news_id String COMMENT '新闻唯一ID（格式：source_原始id）',
    source String COMMENT '来源：cls/eastmoney/cninfo',
    publish_time DateTime COMMENT '发布时间',
    title String COMMENT '标题',
    content String COMMENT '正文',
    url Nullable(String) COMMENT '新闻链接',
    raw_json Nullable(String) COMMENT '原始JSON数据（用于溯源）',
    first_seen_time Nullable(DateTime) COMMENT '系统首次发现时间',
    delay_seconds Nullable(Int32) COMMENT '发现延迟（秒）',
    created_at DateTime DEFAULT now() COMMENT '入库时间'
)
ENGINE = ReplacingMergeTree(created_at)
ORDER BY (source, publish_time, news_id)
COMMENT '原始新闻表（采集层输出）';
