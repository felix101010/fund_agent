-- 初始化 ClickHouse 数据库脚本
-- 按顺序执行所有表创建语句

-- 使用说明：
-- 1. 确保 ClickHouse 服务已启动
-- 2. 执行: clickhouse-client --multiquery < sql/clickhouse/000_init_all.sql
-- 或者在 Python 中使用 ClickHouseClient 逐个执行

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS quant;
USE quant;

-- P0 核心表（按依赖顺序）
-- 1. 证券主数据表
SOURCE 001_symbol_master.sql;

-- 2. 统一日线行情表
SOURCE 002_daily_bars.sql;

-- 3. 数据源状态表
SOURCE 003_source_status.sql;

-- 4. 任务运行日志表
SOURCE 004_job_run_log.sql;

-- 5. 原始新闻表
SOURCE 005_raw_news.sql;

-- 6. 新闻事件抽取结果表
SOURCE 006_extracted_events.sql;

-- 验证表创建
SHOW TABLES;

-- 查看表结构示例
-- DESC symbol_master;
-- DESC daily_bars;
-- DESC source_status;
-- DESC job_run_log;
-- DESC raw_news;
-- DESC extracted_events;
