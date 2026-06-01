#!/usr/bin/env python
"""
初始化 ClickHouse 数据库
创建所有必需的表
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.data.storage.clickhouse_client import ClickHouseClient
from fund_quant.common.logger import logger


def init_clickhouse():
    """初始化 ClickHouse 数据库"""

    logger.info("=" * 60)
    logger.info("开始初始化 ClickHouse 数据库")
    logger.info("=" * 60)

    # 初始化客户端
    client = ClickHouseClient()

    # 确保使用正确的数据库
    client.execute("USE quant")
    logger.info("切换到数据库: quant")

    # SQL 文件目录
    sql_dir = project_root / "sql" / "clickhouse"

    # 按顺序执行的 SQL 文件
    sql_files = [
        "001_symbol_master.sql",
        "002_daily_bars.sql",
        "003_source_status.sql",
        "004_job_run_log.sql",
        "005_raw_news.sql",
        "006_extracted_events.sql",
    ]

    success_count = 0
    failed_count = 0

    for sql_file in sql_files:
        sql_path = sql_dir / sql_file

        if not sql_path.exists():
            logger.error(f"SQL 文件不存在: {sql_path}")
            failed_count += 1
            continue

        logger.info(f"\n执行: {sql_file}")

        try:
            # 读取 SQL 文件
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # 分割多个语句（以分号分隔）
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]

            for stmt in statements:
                # 跳过注释行
                if stmt.startswith('--') or stmt.startswith('/*'):
                    continue

                # 跳过 ALTER INDEX 语句（需要表已存在）
                if 'ALTER TABLE' in stmt and 'ADD INDEX' in stmt:
                    logger.debug(f"跳过索引创建（稍后执行）: {stmt[:50]}...")
                    continue

                # 执行语句
                client.execute(stmt)

            logger.info(f"✓ {sql_file} 执行成功")
            success_count += 1

        except Exception as e:
            logger.error(f"✗ {sql_file} 执行失败: {e}")
            failed_count += 1

    # 创建索引（第二遍）
    logger.info("\n" + "=" * 60)
    logger.info("创建索引")
    logger.info("=" * 60)

    for sql_file in sql_files:
        sql_path = sql_dir / sql_file

        if not sql_path.exists():
            continue

        try:
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            statements = [s.strip() for s in sql_content.split(';') if s.strip()]

            for stmt in statements:
                if 'ALTER TABLE' in stmt and 'ADD INDEX' in stmt:
                    try:
                        client.execute(stmt)
                        logger.debug(f"✓ 索引创建成功")
                    except Exception as e:
                        # 索引可能已存在，忽略错误
                        if 'already exists' in str(e).lower():
                            logger.debug(f"索引已存在，跳过")
                        else:
                            logger.warning(f"索引创建失败: {e}")

        except Exception as e:
            logger.warning(f"处理索引时出错: {e}")

    # 验证表创建
    logger.info("\n" + "=" * 60)
    logger.info("验证表创建")
    logger.info("=" * 60)

    tables = client.query_df("SHOW TABLES")

    if tables is not None and len(tables) > 0:
        logger.info(f"\n已创建的表 ({len(tables)} 个):")
        for table in tables['name'].tolist():
            logger.info(f"  - {table}")
    else:
        logger.warning("未找到任何表")

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("初始化完成")
    logger.info("=" * 60)
    logger.info(f"成功: {success_count} 个")
    logger.info(f"失败: {failed_count} 个")

    if failed_count == 0:
        logger.info("\n✓ 所有表创建成功！")
        return True
    else:
        logger.warning(f"\n⚠ 有 {failed_count} 个表创建失败")
        return False


if __name__ == "__main__":
    try:
        success = init_clickhouse()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)
