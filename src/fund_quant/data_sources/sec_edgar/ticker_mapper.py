"""
Ticker 到 CIK 映射器
从 SEC 官方数据源获取映射关系
"""
import requests
from typing import Dict, Optional
from pathlib import Path
import json

from fund_quant.data_sources.sec_edgar.sec_config import (
    SEC_TICKER_JSON_URL,
    SEC_USER_AGENT,
    SEC_TIMEOUT
)


class TickerMapper:
    """
    Ticker 到 CIK 映射器

    职责：
    1. 从SEC官方数据源获取ticker映射
    2. Ticker → CIK
    3. CIK补齐10位
    """

    def __init__(self, cache_file: str = "data/cache/sec_ticker_cik_map.json"):
        """
        初始化

        Args:
            cache_file: 缓存文件路径
        """
        self.cache_file = Path(cache_file)
        self.ticker_to_cik: Dict[str, str] = {}
        self.cik_to_ticker: Dict[str, str] = {}

        # 确保缓存目录存在
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载映射
        self._load_mapping()

    def _load_mapping(self):
        """加载映射（优先使用缓存）"""
        # 尝试从缓存加载
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.ticker_to_cik = data.get('ticker_to_cik', {})
                    self.cik_to_ticker = data.get('cik_to_ticker', {})
                    return
            except:
                pass

        # 从SEC下载
        self._download_mapping()

    def _download_mapping(self):
        """从SEC官方下载映射"""
        headers = {'User-Agent': SEC_USER_AGENT}

        try:
            response = requests.get(
                SEC_TICKER_JSON_URL,
                headers=headers,
                timeout=SEC_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()

            # 解析数据
            # data格式: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
            for item in data.values():
                cik_str = str(item.get('cik_str', ''))
                ticker = item.get('ticker', '').upper()

                if cik_str and ticker:
                    # CIK补齐10位
                    cik_padded = self.pad_cik(cik_str)
                    self.ticker_to_cik[ticker] = cik_padded
                    self.cik_to_ticker[cik_padded] = ticker

            # 保存缓存
            self._save_cache()

        except Exception as e:
            print(f"⚠️  下载SEC ticker映射失败: {str(e)}")

    def _save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'ticker_to_cik': self.ticker_to_cik,
                    'cik_to_ticker': self.cik_to_ticker
                }, f, indent=2)
        except:
            pass

    def get_cik(self, ticker: str) -> Optional[str]:
        """
        获取CIK（已补齐10位）

        Args:
            ticker: 股票代码

        Returns:
            CIK（10位），未找到返回None
        """
        return self.ticker_to_cik.get(ticker.upper())

    def get_ticker(self, cik: str) -> Optional[str]:
        """
        获取Ticker

        Args:
            cik: CIK

        Returns:
            Ticker，未找到返回None
        """
        cik_padded = self.pad_cik(cik)
        return self.cik_to_ticker.get(cik_padded)

    @staticmethod
    def pad_cik(cik: str) -> str:
        """
        CIK补齐10位

        Args:
            cik: 原始CIK

        Returns:
            补齐后的CIK

        Examples:
            >>> TickerMapper.pad_cik("1045810")
            '0001045810'
            >>> TickerMapper.pad_cik("320193")
            '0000320193'
        """
        cik_str = str(cik).strip()
        return cik_str.zfill(10)

    @staticmethod
    def remove_cik_leading_zeros(cik: str) -> str:
        """
        移除CIK前导零（用于拼接Archives URL）

        Args:
            cik: CIK

        Returns:
            移除前导零的CIK

        Examples:
            >>> TickerMapper.remove_cik_leading_zeros("0001045810")
            '1045810'
        """
        return str(int(cik))


__all__ = ['TickerMapper']
