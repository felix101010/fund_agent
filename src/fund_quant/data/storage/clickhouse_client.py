"""
ClickHouse 数据访问层
提供统一的数据库操作接口
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError

from fund_quant.common.config import settings
from fund_quant.common.logger import logger


class ClickHouseClient:
    """ClickHouse 客户端"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        """
        初始化 ClickHouse 客户端

        Args:
            host: 主机地址
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
        """
        self.host = host or settings.clickhouse_host
        self.port = port or settings.clickhouse_port
        self.user = user or settings.clickhouse_user
        self.password = password or settings.clickhouse_password
        self.database = database or settings.clickhouse_db

        self.client = None
        self._connect()

    def _connect(self):
        """建立连接"""
        try:
            self.client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )

            # 测试连接
            self.client.execute('SELECT 1')
            logger.info(f"ClickHouse 连接成功: {self.host}:{self.port}/{self.database}")

        except Exception as e:
            logger.error(f"ClickHouse 连接失败: {e}")
            raise

    def execute(self, sql: str, params: Optional[Dict] = None) -> Any:
        """
        执行 SQL 语句

        Args:
            sql: SQL 语句
            params: 参数字典

        Returns:
            执行结果
        """
        try:
            if params:
                result = self.client.execute(sql, params)
            else:
                result = self.client.execute(sql)
            return result
        except ClickHouseError as e:
            logger.error(f"SQL 执行失败: {sql[:100]}... 错误: {e}")
            raise

    def query_df(self, sql: str, params: Optional[Dict] = None) -> Optional[pd.DataFrame]:
        """
        查询并返回 DataFrame

        Args:
            sql: SQL 查询语句
            params: 参数字典

        Returns:
            DataFrame 或 None
        """
        try:
            if params:
                result = self.client.execute(sql, params, with_column_types=True)
            else:
                result = self.client.execute(sql, with_column_types=True)

            if not result:
                return None

            data, columns = result
            column_names = [col[0] for col in columns]

            if not data:
                return pd.DataFrame(columns=column_names)

            df = pd.DataFrame(data, columns=column_names)
            return df

        except ClickHouseError as e:
            logger.error(f"查询失败: {sql[:100]}... 错误: {e}")
            return None

    def insert_many(
        self,
        table: str,
        rows: List[Dict[str, Any]],
        batch_size: int = 10000
    ) -> int:
        """
        批量插入数据

        Args:
            table: 表名
            rows: 数据行列表
            batch_size: 批次大小

        Returns:
            成功插入的行数
        """
        if not rows:
            return 0

        total_inserted = 0

        try:
            # 获取列名
            columns = list(rows[0].keys())

            # 分批插入
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]

                # 构建插入语句
                values = []
                for row in batch:
                    values.append([row.get(col) for col in columns])

                sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES"

                self.client.execute(sql, values)
                total_inserted += len(batch)

                logger.debug(f"插入 {table}: {len(batch)} 行 (总计: {total_inserted}/{len(rows)})")

            logger.info(f"✓ 成功插入 {table}: {total_inserted} 行")
            return total_inserted

        except ClickHouseError as e:
            logger.error(f"批量插入失败 {table}: {e}")
            raise

    def update_source_status(
        self,
        source_name: str,
        data_type: str,
        status: str,
        last_trade_date: Optional[str] = None,
        last_id: Optional[str] = None,
        error_message: Optional[str] = None,
        rows_processed: int = 0,
        metadata: Optional[Dict] = None
    ):
        """
        更新数据源状态

        Args:
            source_name: 数据源名称
            data_type: 数据类型
            status: 状态
            last_trade_date: 最后交易日期
            last_id: 最后ID
            error_message: 错误信息
            rows_processed: 处理行数
            metadata: 元数据
        """
        import json

        row = {
            'source_name': source_name,
            'data_type': data_type,
            'last_success_time': datetime.now(),
            'last_trade_date': last_trade_date,
            'last_id': last_id,
            'status': status,
            'error_message': error_message,
            'rows_processed': rows_processed,
            'metadata': json.dumps(metadata or {}),
            'updated_at': datetime.now()
        }

        try:
            self.insert_many('source_status', [row])
            logger.debug(f"更新数据源状态: {source_name}/{data_type} -> {status}")
        except Exception as e:
            logger.error(f"更新数据源状态失败: {e}")

    def write_job_run_log(
        self,
        job_name: str,
        source_name: str,
        start_time: datetime,
        status: str,
        end_time: Optional[datetime] = None,
        rows_read: int = 0,
        rows_written: int = 0,
        rows_failed: int = 0,
        error_message: Optional[str] = None,
        params: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        写入任务运行日志

        Args:
            job_name: 任务名称
            source_name: 数据源名称
            start_time: 开始时间
            status: 状态
            end_time: 结束时间
            rows_read: 读取行数
            rows_written: 写入行数
            rows_failed: 失败行数
            error_message: 错误信息
            params: 任务参数
            metadata: 元数据

        Returns:
            任务ID
        """
        import json

        job_id = str(uuid.uuid4())

        row = {
            'job_id': job_id,
            'job_name': job_name,
            'source_name': source_name,
            'start_time': start_time,
            'end_time': end_time or datetime.now(),
            'status': status,
            'rows_read': rows_read,
            'rows_written': rows_written,
            'rows_failed': rows_failed,
            'error_message': error_message,
            'params': json.dumps(params or {}),
            'metadata': json.dumps(metadata or {}),
            'created_at': datetime.now()
        }

        try:
            self.insert_many('job_run_log', [row])
            logger.debug(f"写入任务日志: {job_name} ({job_id}) -> {status}")
            return job_id
        except Exception as e:
            logger.error(f"写入任务日志失败: {e}")
            return job_id

    def get_latest_trade_date(self, symbol: str, asset_type: str) -> Optional[str]:
        """
        获取某个证券的最新交易日期

        Args:
            symbol: 证券代码
            asset_type: 资产类型

        Returns:
            最新交易日期（YYYYMMDD格式）或 None
        """
        sql = """
        SELECT max(trade_date) as latest_date
        FROM daily_bars
        WHERE symbol = %(symbol)s AND asset_type = %(asset_type)s
        """

        df = self.query_df(sql, {'symbol': symbol, 'asset_type': asset_type})

        if df is not None and len(df) > 0 and df['latest_date'].iloc[0]:
            date = df['latest_date'].iloc[0]
            return date.strftime('%Y%m%d')

        return None

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.disconnect()
            logger.info("ClickHouse 连接已关闭")
