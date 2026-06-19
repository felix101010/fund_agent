"""
美股公司投资者关系（IR）配置（扩展版）
支持30+核心股票的分层配置
"""

# 公司IR配置（分层）
IR_COMPANIES = {
    # ==================== TIER 1: 核心公司 ====================
    
    "NVDA": {
        "company_name": "NVIDIA",
        "ir_home": "https://investor.nvidia.com",
        "rss_urls": [
            "https://nvidianews.nvidia.com/releases.xml",
            "https://nvidianews.nvidia.com/cats/press_release.xml",
            "https://investor.nvidia.com/rss/Event.aspx?LanguageId=1"
        ],
        "rss_discovery_urls": [
            "https://investor.nvidia.com/investor-resources/rss/default.aspx",
            "https://nvidianews.nvidia.com/rss"
        ],
        "newsroom_url": "https://nvidianews.nvidia.com/news",
        "enabled": True,
        "tier": 1,
        "themes": ["AI_chip", "data_center", "GPU", "automotive"],
        "rule_profile": "nvidia"
    },
    
    "MSFT": {
        "company_name": "Microsoft",
        "ir_home": "https://www.microsoft.com/en-us/investor",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://www.microsoft.com/en-us/investor",
            "https://news.microsoft.com"
        ],
        "newsroom_url": "https://news.microsoft.com",
        "enabled": True,
        "tier": 1,
        "themes": ["cloud", "AI", "enterprise_software", "Azure"],
        "rule_profile": "microsoft"
    },
    
    "AAPL": {
        "company_name": "Apple",
        "ir_home": "https://investor.apple.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://www.apple.com/newsroom/rss-feed.rss"
        ],
        "newsroom_url": "https://www.apple.com/newsroom/",
        "enabled": True,
        "tier": 1,
        "themes": ["consumer_electronics", "AI", "services"],
        "rule_profile": "apple"
    },
    
    "GOOGL": {
        "company_name": "Alphabet/Google",
        "ir_home": "https://abc.xyz/investor/",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://abc.xyz/investor/",
            "https://blog.google/rss/"
        ],
        "newsroom_url": "https://blog.google",
        "enabled": True,
        "tier": 1,
        "themes": ["search", "cloud", "AI", "advertising"],
        "rule_profile": "google"
    },
    
    "AMZN": {
        "company_name": "Amazon",
        "ir_home": "https://ir.aboutamazon.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://ir.aboutamazon.com/news-releases",
            "https://press.aboutamazon.com"
        ],
        "newsroom_url": "https://press.aboutamazon.com",
        "enabled": True,
        "tier": 1,
        "themes": ["e-commerce", "cloud", "AWS", "logistics"],
        "rule_profile": "amazon"
    },
    
    "META": {
        "company_name": "Meta",
        "ir_home": "https://investor.fb.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investor.fb.com/news/default.aspx",
            "https://about.fb.com/news"
        ],
        "newsroom_url": "https://about.fb.com/news",
        "enabled": True,
        "tier": 1,
        "themes": ["social_media", "VR", "AI", "advertising"],
        "rule_profile": "meta"
    },
    
    "TSLA": {
        "company_name": "Tesla",
        "ir_home": "https://ir.tesla.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://ir.tesla.com/press"
        ],
        "press_url": "https://ir.tesla.com/press",
        "enabled": True,
        "tier": 1,
        "themes": ["EV", "autonomous", "energy_storage", "AI"],
        "rule_profile": "tesla"
    },
    
    "AVGO": {
        "company_name": "Broadcom",
        "ir_home": "https://investors.broadcom.com",
        "press_url": "https://investors.broadcom.com/news-releases",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investors.broadcom.com/news-releases",
            "https://www.broadcom.com/company/news"
        ],
        "page_fallback_urls": [
            "https://investors.broadcom.com/news-releases",
            "https://www.broadcom.com/company/news"
        ],
        "enabled": True,
        "tier": 1,
        "themes": ["AI_ASIC", "networking", "semiconductor"],
        "rule_profile": "semiconductor"
    },
    
    "AMD": {
        "company_name": "AMD",
        "ir_home": "https://ir.amd.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://ir.amd.com/news-events/press-releases",
            "https://www.amd.com/en/newsroom.html"
        ],
        "newsroom_url": "https://www.amd.com/en/newsroom.html",
        "enabled": True,
        "tier": 1,
        "themes": ["CPU", "GPU", "data_center", "AI_chip"],
        "rule_profile": "semiconductor"
    },
    
    "TSM": {
        "company_name": "TSMC",
        "ir_home": "https://investor.tsmc.com",
        "press_url": "https://pr.tsmc.com/english/news",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://pr.tsmc.com/english/news",
            "https://investor.tsmc.com/english/news-events/news"
        ],
        "page_fallback_urls": [
            "https://pr.tsmc.com/english/news",
            "https://investor.tsmc.com/english/news-events/news"
        ],
        "enabled": True,
        "tier": 1,
        "themes": ["foundry", "semiconductor_manufacturing", "advanced_node"],
        "rule_profile": "semiconductor_foundry"
    },
    
    # ==================== TIER 2: 重点主题公司 ====================

    "ASML": {
        "company_name": "ASML",
        "ir_home": "https://www.asml.com",
        "press_url": "https://www.asml.com/en/news/press-releases",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://www.asml.com/en/news"
        ],
        "page_fallback_urls": [
            "https://www.asml.com/en/news/press-releases"
        ],
        "enabled": True,
        "tier": 2,
        "themes": ["EUV", "lithography", "semiconductor_equipment"],
        "rule_profile": "semiconductor_equipment"
    },

    "MU": {
        "company_name": "Micron Technology",
        "ir_home": "https://investors.micron.com",
        "press_url": "https://investors.micron.com/news-releases",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investors.micron.com/news-releases",
            "https://investors.micron.com/news-events/press-releases"
        ],
        "page_fallback_urls": [
            "https://investors.micron.com/news-releases",
            "https://investors.micron.com/news-events/press-releases"
        ],
        "enabled": True,
        "tier": 2,
        "themes": ["HBM", "DRAM", "NAND", "memory", "AI_memory"],
        "rule_profile": "semiconductor"
    },

    "MRVL": {
        "company_name": "Marvell",
        "ir_home": "https://investor.marvell.com",
        "press_url": "https://investor.marvell.com/news-events/press-releases",
        "rss_urls": [
            "https://investor.marvell.com/news-events/press-releases/rss"
        ],
        "rss_discovery_urls": [
            "https://investor.marvell.com/news-releases",
            "https://investor.marvell.com/news-events/press-releases"
        ],
        "page_fallback_urls": [
            "https://investor.marvell.com/news-events/press-releases"
        ],
        "enabled": True,
        "tier": 2,
        "themes": ["AI_networking", "custom_silicon", "data_center", "optical", "PCIe", "CXL"],
        "rule_profile": "semiconductor"
    },

    "ARM": {
        "company_name": "Arm Holdings",
        "ir_home": "https://ir.arm.com",
        "press_url": "https://ir.arm.com/news",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://ir.arm.com/news"
        ],
        "page_fallback_urls": [
            "https://ir.arm.com/news"
        ],
        "enabled": True,
        "tier": 2,
        "themes": ["CPU_IP", "AI_edge", "mobile_chip"],
        "rule_profile": "semiconductor"
    },

    "INTC": {
        "company_name": "Intel",
        "ir_home": "https://www.intc.com",
        "press_url": "https://www.intc.com/news-events/press-releases",
        "rss_urls": [
            "https://www.intc.com/news-events/press-releases/rss"
        ],
        "rss_discovery_urls": [
            "https://www.intc.com/news-events/press-releases"
        ],
        "page_fallback_urls": [
            "https://www.intc.com/news-events/press-releases"
        ],
        "newsroom_url": "https://newsroom.intel.com",
        "enabled": True,
        "tier": 2,
        "themes": ["CPU", "foundry", "AI_PC", "AI_infrastructure", "semiconductor_policy"],
        "rule_profile": "semiconductor"
    },

    "AMAT": {
        "company_name": "Applied Materials",
        "ir_home": "https://www.appliedmaterials.com",
        "press_url": "https://ir.appliedmaterials.com/news-releases",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://www.appliedmaterials.com/us/en/about/news.html",
            "https://ir.appliedmaterials.com/news-releases"
        ],
        "page_fallback_urls": [
            "https://www.appliedmaterials.com/us/en/about/news.html",
            "https://ir.appliedmaterials.com/news-releases"
        ],
        "enabled": True,
        "tier": 2,
        "themes": ["semiconductor_equipment", "materials_engineering", "wafer_fab_equipment"],
        "rule_profile": "semiconductor_equipment"
    },

    "LRCX": {
        "company_name": "Lam Research",
        "ir_home": "https://investor.lamresearch.com",
        "press_url": "https://investor.lamresearch.com/news-releases",
        "rss_urls": [
            "https://investor.lamresearch.com/index.php?s=43&pagetemplate=rss"
        ],
        "rss_discovery_urls": [
            "https://investor.lamresearch.com/news-releases"
        ],
        "page_fallback_urls": [
            "https://investor.lamresearch.com/news-releases"
        ],
        "enabled": True,
        "tier": 2,
        "themes": ["semiconductor_equipment", "etch", "deposition", "wafer_fab_equipment"],
        "rule_profile": "semiconductor_equipment"
    },

    "KLAC": {
        "company_name": "KLA",
        "ir_home": "https://ir.kla.com",
        "press_url": "https://ir.kla.com/news-events/press-releases",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://ir.kla.com/news-events/press-releases",
            "https://www.kla.com/newsroom"
        ],
        "page_fallback_urls": [
            "https://ir.kla.com/news-events/press-releases",
            "https://www.kla.com/newsroom"
        ],
        "enabled": True,
        "tier": 2,
        "themes": ["process_control", "inspection", "metrology", "semiconductor_equipment"],
        "rule_profile": "semiconductor_equipment"
    },

    "ORCL": {
        "company_name": "Oracle",
        "ir_home": "https://investor.oracle.com",
        "press_url": "https://investor.oracle.com/news/news-details/default.aspx",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investor.oracle.com/news/news-details/default.aspx",
            "https://www.oracle.com/news/"
        ],
        "page_fallback_urls": [
            "https://investor.oracle.com/news/news-details/default.aspx",
            "https://www.oracle.com/news/"
        ],
        "newsroom_url": "https://www.oracle.com/news/",
        "enabled": True,
        "tier": 2,
        "themes": ["cloud", "AI_infrastructure", "database", "enterprise_software"],
        "rule_profile": "software"
    },

    "PLTR": {
        "company_name": "Palantir",
        "ir_home": "https://investors.palantir.com",
        "press_url": "https://investors.palantir.com/news-events/press-releases",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investors.palantir.com/news-details",
            "https://investors.palantir.com/news-events/press-releases"
        ],
        "page_fallback_urls": [
            "https://investors.palantir.com/news-details",
            "https://investors.palantir.com/news-events/press-releases"
        ],
        "enabled": True,
        "tier": 2,
        "themes": ["AI_software", "government", "defense", "data_platform"],
        "rule_profile": "software"
    },
    
    # ==================== TIER 3: 观察公司 ====================
    
    "CRM": {
        "company_name": "Salesforce",
        "ir_home": "https://investor.salesforce.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investor.salesforce.com/press-releases/"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["CRM", "cloud", "enterprise_software"],
        "rule_profile": "software"
    },
    
    "NOW": {
        "company_name": "ServiceNow",
        "ir_home": "https://investors.servicenow.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investors.servicenow.com/news/"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["IT_service", "workflow", "AI"],
        "rule_profile": "software"
    },
    
    "SNOW": {
        "company_name": "Snowflake",
        "ir_home": "https://investors.snowflake.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investors.snowflake.com/news/"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["data_warehouse", "cloud", "analytics"],
        "rule_profile": "software"
    },
    
    "ADBE": {
        "company_name": "Adobe",
        "ir_home": "https://www.adobe.com/investor-relations.html",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://news.adobe.com"
        ],
        "newsroom_url": "https://news.adobe.com",
        "enabled": False,
        "tier": 3,
        "themes": ["creative_software", "AI", "digital_marketing"],
        "rule_profile": "software"
    },
    
    "CRWD": {
        "company_name": "CrowdStrike",
        "ir_home": "https://ir.crowdstrike.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://ir.crowdstrike.com/news-releases"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["cybersecurity", "endpoint_security", "AI"],
        "rule_profile": "software"
    },
    
    "PANW": {
        "company_name": "Palo Alto Networks",
        "ir_home": "https://investors.paloaltonetworks.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investors.paloaltonetworks.com/news-releases"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["cybersecurity", "firewall", "AI"],
        "rule_profile": "software"
    },
    
    "NET": {
        "company_name": "Cloudflare",
        "ir_home": "https://investors.cloudflare.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investors.cloudflare.com/news-releases"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["CDN", "security", "edge_computing"],
        "rule_profile": "software"
    },
    
    "COIN": {
        "company_name": "Coinbase",
        "ir_home": "https://investor.coinbase.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investor.coinbase.com/news"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["crypto", "exchange", "blockchain"],
        "rule_profile": "crypto"
    },
    
    "MSTR": {
        "company_name": "MicroStrategy",
        "ir_home": "https://www.microstrategy.com/en/investor-relations",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://www.microstrategy.com/en/investor-relations/press-releases"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["crypto", "bitcoin", "business_intelligence"],
        "rule_profile": "crypto"
    },
    
    "HOOD": {
        "company_name": "Robinhood",
        "ir_home": "https://investors.robinhood.com",
        "rss_urls": [],
        "rss_discovery_urls": [
            "https://investors.robinhood.com/news"
        ],
        "enabled": False,
        "tier": 3,
        "themes": ["fintech", "trading", "crypto"],
        "rule_profile": "crypto"
    }
}


def get_ir_company_config(ticker: str) -> dict | None:
    """
    获取公司IR配置

    Args:
        ticker: 股票代码（大小写不敏感）

    Returns:
        配置字典或None
    """
    ticker_upper = ticker.upper()
    return IR_COMPANIES.get(ticker_upper)


def list_enabled_ir_tickers() -> list[str]:
    """
    列出所有启用的IR公司代码

    Returns:
        启用的ticker列表
    """
    return [
        ticker
        for ticker, config in IR_COMPANIES.items()
        if config.get('enabled', False)
    ]


def list_ir_tickers_by_tier(tier: int, include_disabled: bool = False) -> list[str]:
    """
    按tier列出公司代码

    Args:
        tier: 1=核心, 2=重点, 3=观察
        include_disabled: 是否包含未启用的公司

    Returns:
        ticker列表
    """
    return [
        ticker
        for ticker, config in IR_COMPANIES.items()
        if config.get('tier') == tier and (include_disabled or config.get('enabled', False))
    ]


def list_all_ir_tickers(include_disabled: bool = False) -> list[str]:
    """
    列出所有公司代码

    Args:
        include_disabled: 是否包含未启用的公司

    Returns:
        ticker列表
    """
    if include_disabled:
        return list(IR_COMPANIES.keys())
    else:
        return list_enabled_ir_tickers()


__all__ = [
    'IR_COMPANIES',
    'get_ir_company_config',
    'list_enabled_ir_tickers',
    'list_ir_tickers_by_tier',
    'list_all_ir_tickers'
]
