"""
新闻去重管理器
支持 ClickHouse 查询和本地文件 fallback
"""
import os
from pathlib import Path
from typing import Set, List
from datetime import datetime


class NewsDedupManager:
    """
    新闻去重管理器

    职责：
    1. 判断 news_id 是否已存在
    2. 优先使用 ClickHouse 查询
    3. ClickHouse 不可用时使用本地文件
    4. 写入 raw_news 表（可选）
    """

    def __init__(
        self,
        seen_file_path: str = "data/review/seen_cls_news_ids.txt",
        use_clickhouse: bool = False,
        clickhouse_client=None
    ):
        """
        初始化

        Args:
            seen_file_path: 本地去重文件路径
            use_clickhouse: 是否使用 ClickHouse
            clickhouse_client: ClickHouse 客户端
        """
        self.seen_file_path = Path(seen_file_path)
        self.use_clickhouse = use_clickhouse
        self.clickhouse_client = clickhouse_client
        self.seen_ids: Set[str] = set()

        # 确保目录存在
        self.seen_file_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载已seen的news_id
        self._load_seen_ids()

    def _load_seen_ids(self):
        """从本地文件加载已seen的news_id"""
        if self.seen_file_path.exists():
            with open(self.seen_file_path, 'r', encoding='utf-8') as f:
                self.seen_ids = set(line.strip() for line in f if line.strip())

    def _save_seen_id(self, news_id: str):
        """追加保存news_id到本地文件"""
        with open(self.seen_file_path, 'a', encoding='utf-8') as f:
            f.write(f"{news_id}\n")
        self.seen_ids.add(news_id)

    def is_duplicate(self, news_id: str) -> bool:
        """
        判断 news_id 是否已存在

        Args:
            news_id: 新闻ID

        Returns:
            True表示重复，False表示新增
        """
        # 优先使用 ClickHouse
        if self.use_clickhouse and self.clickhouse_client:
            try:
                query = f"SELECT count(*) FROM raw_news WHERE news_id = '{news_id}'"
                result = self.clickhouse_client.execute(query)
                return result[0][0] > 0
            except Exception:
                # ClickHouse 失败，fallback 到本地文件
                pass

        # 使用本地文件
        return news_id in self.seen_ids

    def mark_as_seen(self, news_id: str):
        """
        标记 news_id 为已seen

        Args:
            news_id: 新闻ID
        """
        if news_id not in self.seen_ids:
            self._save_seen_id(news_id)

    def save_raw_news(self, news_list: List[dict]) -> tuple:
        """
        保存原始新闻到 raw_news 表（可选）

        Args:
            news_list: 新闻列表

        Returns:
            (success_count, error_list)
        """
        if not self.use_clickhouse or not self.clickhouse_client:
            return 0, []

        success_count = 0
        errors = []

        for news in news_list:
            try:
                query = """
                INSERT INTO raw_news (
                    news_id, source, title, content,
                    publish_time, url, created_at, status
                ) VALUES
                """
                values = f"""(
                    '{news.get('news_id', '')}',
                    '{news.get('source', '')}',
                    '{news.get('title', '').replace("'", "''")}',
                    '{news.get('content', '').replace("'", "''")}',
                    '{news.get('publish_time', datetime.now())}',
                    '{news.get('url', '')}',
                    now(),
                    'pending'
                )"""

                self.clickhouse_client.execute(query + values)
                success_count += 1
            except Exception as e:
                errors.append(f"{news.get('news_id', 'unknown')}: {str(e)}")

        return success_count, errors


__all__ = ['NewsDedupManager']
