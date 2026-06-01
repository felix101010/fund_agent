"""
Tushare API 限速器
严格执行限速策略，避免触发冷却期
"""
import time
from datetime import datetime
from typing import Optional
from pathlib import Path
import yaml

from fund_quant.common.logger import logger


class RateLimiter:
    """
    Tushare API 限速器

    功能：
    1. 基础限速：每次请求间隔至少 base_interval 秒
    2. 批次限速：连续请求N次后强制冷却
    3. 请求计数：统计请求次数和时间
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化限速器

        Args:
            config_path: 配置文件路径，默认使用 configs/data_sources/rate_limit.yaml
        """
        if config_path is None:
            # 从项目根目录查找配置文件
            project_root = Path(__file__).parent.parent.parent.parent.parent
            config_path = project_root / "configs" / "data_sources" / "rate_limit.yaml"

        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.tushare_config = config['tushare']
        self.base_interval = self.tushare_config['base_interval']
        self.batch_limits = self.tushare_config['batch_limits']

        # 状态变量
        self.last_request_time: Optional[float] = None
        self.request_count = 0
        self.total_requests = 0
        self.total_wait_time = 0.0

        logger.info(f"限速器初始化: base_interval={self.base_interval}s")
        for limit in self.batch_limits:
            logger.info(f"  批次限制: {limit['requests']}次请求后冷却{limit['cooldown']}秒")

    def wait(self, endpoint: Optional[str] = None) -> float:
        """
        等待直到可以发起下一次请求

        Args:
            endpoint: 接口名称（可选，用于特定接口限速）

        Returns:
            实际等待时间（秒）
        """
        total_wait = 0.0

        # 1. 基础限速：确保与上次请求间隔至少 base_interval 秒
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.base_interval:
                base_wait = self.base_interval - elapsed
                logger.debug(f"基础限速: 等待 {base_wait:.3f}s")
                time.sleep(base_wait)
                total_wait += base_wait

        # 2. 批次限速：检查是否需要冷却
        for limit in self.batch_limits:
            if self.request_count >= limit['requests']:
                cooldown = limit['cooldown']
                logger.warning(f"批次限速触发: 已连续请求{self.request_count}次，冷却{cooldown}秒")
                time.sleep(cooldown)
                total_wait += cooldown
                self.request_count = 0  # 重置计数
                break

        # 3. 更新状态
        self.last_request_time = time.time()
        self.request_count += 1
        self.total_requests += 1
        self.total_wait_time += total_wait

        return total_wait

    def reset_batch_counter(self):
        """重置批次计数器"""
        self.request_count = 0
        logger.debug("批次计数器已重置")

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return {
            'total_requests': self.total_requests,
            'total_wait_time': self.total_wait_time,
            'avg_wait_time': self.total_wait_time / self.total_requests if self.total_requests > 0 else 0,
            'current_batch_count': self.request_count
        }

    def log_stats(self):
        """输出统计信息到日志"""
        stats = self.get_stats()
        logger.info("=" * 60)
        logger.info("限速器统计")
        logger.info("=" * 60)
        logger.info(f"总请求次数: {stats['total_requests']}")
        logger.info(f"总等待时间: {stats['total_wait_time']:.1f}秒")
        logger.info(f"平均等待时间: {stats['avg_wait_time']:.3f}秒/次")
        logger.info(f"当前批次计数: {stats['current_batch_count']}")
        logger.info("=" * 60)
