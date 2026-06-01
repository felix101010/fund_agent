#!/bin/bash
# 初始化 ClickHouse 数据库表
# 使用 docker exec 直接在容器中执行 SQL

set -e

echo "============================================================"
echo "初始化 ClickHouse 数据库"
echo "============================================================"

# SQL 文件目录
SQL_DIR="sql/clickhouse"

# 按顺序执行的 SQL 文件
SQL_FILES=(
    "001_symbol_master.sql"
    "002_daily_bars.sql"
    "003_source_status.sql"
    "004_job_run_log.sql"
    "005_raw_news.sql"
    "006_extracted_events.sql"
)

# 执行每个 SQL 文件
for sql_file in "${SQL_FILES[@]}"; do
    echo ""
    echo "执行: $sql_file"

    if docker exec -i fund_quant_clickhouse clickhouse-client --database quant < "$SQL_DIR/$sql_file" 2>&1 | grep -v "Received exception"; then
        echo "✓ $sql_file 执行成功"
    else
        echo "✗ $sql_file 执行失败"
    fi
done

# 验证表创建
echo ""
echo "============================================================"
echo "验证表创建"
echo "============================================================"

tables=$(docker exec fund_quant_clickhouse clickhouse-client --query "SHOW TABLES FROM quant")

if [ -n "$tables" ]; then
    echo ""
    echo "已创建的表:"
    echo "$tables" | while read table; do
        echo "  - $table"
    done
    echo ""
    echo "✓ 所有表创建成功！"
else
    echo ""
    echo "⚠ 未找到任何表"
    exit 1
fi
