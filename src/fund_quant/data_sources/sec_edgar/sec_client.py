"""
SEC 官方接口客户端
实现限流、重试、错误处理
"""
import requests
import time
from typing import Dict, Any, Optional
from datetime import datetime

from fund_quant.data_sources.sec_edgar.sec_config import (
    SEC_USER_AGENT,
    SEC_TIMEOUT,
    SEC_REQUEST_RATE,
    SEC_DATA_URL
)


class SECClient:
    """
    SEC 官方接口客户端

    职责：
    1. 请求限流（遵守SEC Fair Access）
    2. 统一请求头（User-Agent）
    3. 错误处理和重试
    """

    def __init__(self, rate_limit: float = SEC_REQUEST_RATE, timeout: int = SEC_TIMEOUT):
        """
        初始化

        Args:
            rate_limit: 每秒请求数（默认2）
            timeout: 请求超时时间（秒，默认30）
        """
        self.rate_limit = rate_limit
        self.min_interval = 1.0 / rate_limit  # 最小请求间隔
        self.last_request_time = 0.0
        self.timeout = timeout  # 增加timeout属性

        self.headers = {
            'User-Agent': SEC_USER_AGENT,
            'Accept': 'application/json'
        }

    def _wait_for_rate_limit(self):
        """等待以遵守限流"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def get_submissions(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        获取公司submissions

        Args:
            cik: CIK（必须是10位）

        Returns:
            submissions JSON，失败返回None
        """
        url = f"{SEC_DATA_URL}/submissions/CIK{cik}.json"

        try:
            self._wait_for_rate_limit()
            response = requests.get(url, headers=self.headers, timeout=SEC_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  获取submissions失败 (CIK={cik}): {str(e)}")
            return None

    def download_filing(self, url: str) -> Optional[str]:
        """
        下载filing正文

        Args:
            url: Filing URL

        Returns:
            正文内容，失败返回None
        """
        return self.get_text(url)

    def get_text(self, url: str) -> Optional[str]:
        """
        获取文本内容（统一封装）

        Args:
            url: URL

        Returns:
            文本内容，失败返回None
        """
        try:
            self._wait_for_rate_limit()
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"⚠️  下载失败 ({url}): {str(e)}")
            return None

    def get_json(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取JSON内容（统一封装）

        Args:
            url: URL

        Returns:
            JSON内容，失败返回None
        """
        try:
            self._wait_for_rate_limit()
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  下载JSON失败 ({url}): {str(e)}")
            return None


__all__ = ['SECClient']
