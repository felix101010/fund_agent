"""
重试策略
支持指数退避和冷却期检测
"""
import time
from typing import Callable, Optional, Any
from pathlib import Path
import yaml

from fund_quant.common.logger import logger


class RetryPolicy:
    """
    重试策略

    功能：
    1. 指数退避重试
    2. 冷却期检测
    3. 最大重试次数限制
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化重试策略

        Args:
            config_path: 配置文件路径
        """
        if config_path is None:
            # 从项目根目录查找配置文件
            project_root = Path(__file__).parent.parent.parent.parent.parent
            config_path = project_root / "configs" / "data_sources" / "rate_limit.yaml"

        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        retry_config = config['tushare']['retry']
        self.max_attempts = retry_config['max_attempts']
        self.initial_backoff = retry_config['initial_backoff']
        self.max_backoff = retry_config['max_backoff']
        self.exponential_base = retry_config['exponential_base']
        self.cooldown_keywords = retry_config['cooldown_detection_keywords']
        self.cooldown_wait = retry_config['cooldown_wait']

        logger.info(f"重试策略初始化: max_attempts={self.max_attempts}, initial_backoff={self.initial_backoff}s")

    def is_cooldown_error(self, error_message: str) -> bool:
        """
        检测是否为冷却期错误

        Args:
            error_message: 错误信息

        Returns:
            是否为冷却期错误
        """
        error_lower = error_message.lower()
        for keyword in self.cooldown_keywords:
            if keyword in error_lower:
                return True
        return False

    def calculate_backoff(self, attempt: int) -> float:
        """
        计算退避时间

        Args:
            attempt: 当前尝试次数（从0开始）

        Returns:
            退避时间（秒）
        """
        backoff = self.initial_backoff * (self.exponential_base ** attempt)
        return min(backoff, self.max_backoff)

    def execute(
        self,
        func: Callable,
        *args,
        error_handler: Optional[Callable[[Exception, int], bool]] = None,
        **kwargs
    ) -> Any:
        """
        执行函数并在失败时重试

        Args:
            func: 要执行的函数
            *args: 函数参数
            error_handler: 错误处理函数，返回True表示继续重试，False表示放弃
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            最后一次尝试的异常
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                result = func(*args, **kwargs)

                # 成功，返回结果
                if attempt > 0:
                    logger.info(f"✓ 重试成功 (尝试 {attempt + 1}/{self.max_attempts})")

                return result

            except Exception as e:
                last_exception = e
                error_message = str(e)

                # 检测是否为冷却期错误
                if self.is_cooldown_error(error_message):
                    if attempt < self.max_attempts - 1:
                        logger.warning(f"检测到冷却期错误: {error_message}")
                        logger.warning(f"等待 {self.cooldown_wait} 秒后重试...")
                        time.sleep(self.cooldown_wait)
                        logger.info(f"重试 {attempt + 2}/{self.max_attempts}...")
                        continue
                    else:
                        logger.error(f"已达最大重试次数，冷却期错误: {error_message}")
                        raise

                # 调用自定义错误处理器
                if error_handler:
                    should_retry = error_handler(e, attempt)
                    if not should_retry:
                        logger.warning(f"错误处理器决定放弃重试: {error_message}")
                        raise

                # 如果还有重试机会，执行退避
                if attempt < self.max_attempts - 1:
                    backoff = self.calculate_backoff(attempt)
                    logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_attempts}): {error_message}")
                    logger.info(f"等待 {backoff:.1f} 秒后重试...")
                    time.sleep(backoff)
                else:
                    logger.error(f"已达最大重试次数 ({self.max_attempts}): {error_message}")
                    raise

        # 理论上不会到这里，但为了类型检查
        if last_exception:
            raise last_exception
