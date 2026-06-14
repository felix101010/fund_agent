"""
免费Reuters数据源探测器
统一调度多个探测源

法律说明：
- 仅使用公开聚合源的RSS标题/摘要
- 不访问Reuters付费API
- 不抓取Reuters付费正文
- 不绕过任何paywall
- 输出仅用于个人技术测试和数据源可用性验证
- 如需生产使用Reuters，应使用Reuters/LSEG正式授权API
"""
from typing import List
from fund_quant.data_sources.global_news.google_news_rss_probe import GoogleNewsRSSProbe
from fund_quant.data_sources.global_news.free_news_probe_models import FreeReutersProbeResult


class FreeReutersProbe:
    """
    免费Reuters数据源探测器

    职责：
    - 调度多个免费聚合源探测
    - 返回可用性验证结果
    """

    # 默认查询词列表
    DEFAULT_QUERIES = [
        "Reuters NVIDIA",
        "Reuters TSMC",
        "Reuters Federal Reserve",
        "Reuters oil prices",
        "Reuters China export controls",
        "Reuters AI chips",
        "Reuters Tesla",
        "Reuters ASML",
        "Reuters copper prices",
        "Reuters Apple supply chain"
    ]

    def __init__(self):
        """初始化"""
        self.google_probe = GoogleNewsRSSProbe()

    def run_google_news_probe(self, query: str, max_samples: int = 10) -> FreeReutersProbeResult:
        """
        运行Google News探测

        Args:
            query: 查询词
            max_samples: 最大样本数

        Returns:
            FreeReutersProbeResult
        """
        return self.google_probe.probe(query, max_samples)

    def run_all_default_queries(self, max_samples: int = 10) -> List[FreeReutersProbeResult]:
        """
        运行所有默认查询

        Args:
            max_samples: 每个查询的最大样本数

        Returns:
            List[FreeReutersProbeResult]
        """
        results = []

        for query in self.DEFAULT_QUERIES:
            result = self.run_google_news_probe(query, max_samples)
            results.append(result)

        return results


__all__ = ['FreeReutersProbe']
