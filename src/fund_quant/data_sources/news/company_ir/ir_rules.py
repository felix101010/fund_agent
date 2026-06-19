"""
Company IR新闻规则分类器（增强版）
根据标题和内容自动分类IR新闻类型和评分
"""


class IRRules:
    """
    IR新闻规则分类器（增强版）

    职责：
    - 识别财报新闻稿
    - 识别战略合作
    - 识别AI基础设施
    - 识别产品量产
    - 识别供应链合作
    - 过滤低价值内容
    """

    # 财报日期预告关键词（高优先级，先判断）
    EARNINGS_EVENT_KEYWORDS = [
        "to report financial results",
        "to report first-quarter",
        "to report second-quarter",
        "to report third-quarter",
        "to report fourth-quarter",
        "will report",
        "will release financial results",
        "will post financial results",
        "schedules financial results",
        "announces conference call to review",
        "conference call to review",
        "financial conference call",
        "earnings call scheduled",
        "to announce",
        "scheduled to report",
    ]

    # 财报预告中需要AI的关键词（包含guidance/预警）
    EARNINGS_NOTICE_NEEDS_AI_KEYWORDS = [
        "updated guidance",
        "preliminary results",
        "expected revenue",
        "expects revenue",
        "warns",
        "lowers guidance",
        "raises guidance",
        "outlook",
        "preannounce",
        "pre-announce",
    ]

    # 财报新闻稿关键词（判断预告之后）
    EARNINGS_RELEASE_KEYWORDS = [
        "reports financial results",
        "reports fiscal",
        "reports first quarter",
        "reports second quarter",
        "reports third quarter",
        "reports fourth quarter",
        "reports first-quarter",
        "reports second-quarter",
        "reports third-quarter",
        "reports fourth-quarter",
        "announces financial results",
        "financial results for",
        "quarterly results",
        "earnings release",
        "results for the quarter",
        "preliminary results",
        "preliminary financial results",
        "preannouncement",
        "pre-announcement",
        "warns on",
        "warning on",
        "lowers guidance",
        "lowers outlook",
        "reduces guidance",
    ]

    # 实际财务数字关键词（用于确认是正式财报）
    ACTUAL_FINANCIAL_KEYWORDS = [
        "revenue was", "revenue of $", "net income was",
        "net income of $", "operating income of", "gross margin of",
        "diluted eps", "earnings per share", "gaap eps", "non-gaap eps",
        "$ billion", "$ million", "revenue grew", "revenue increased"
    ]

    # 战略合作关键词
    STRATEGIC_PARTNERSHIP_KEYWORDS = [
        "partnership", "collaborate", "collaboration",
        "multiyear", "alliance", "strategic agreement",
        "joint", "cooperation",
    ]

    # AI基础设施关键词
    AI_INFRASTRUCTURE_KEYWORDS = [
        "ai factory", "sovereign ai",
        "gigawatt-scale", "dsx platform",
        "gpu cloud", "supercomputer", "ai cloud",
        "builds ai infrastructure", "ai infrastructure for",
    ]

    # 产品量产关键词
    PRODUCT_RAMP_KEYWORDS = [
        "ramps into full production", "full production",
        "mass production", "production ramp",
        "launch", "unveils", "introduces", "ships",
    ]

    # 产品发布关键词（更强）
    PRODUCT_LAUNCH_KEYWORDS = [
        "launches",
        "announces availability",
        "industry's first",
        "unveils",
        "introduces",
        "now available",
        "begins shipping",
        "sampling",
        "production",
        "ramp",
    ]

    # AI数据中心互连关键词
    AI_INTERCONNECT_KEYWORDS = [
        "102.4 tbps",
        "260-lane pcie 6.0",
        "pcie 6.0 switch",
        "pcie 7.0",
        "cxl switch",
        "cxl 3.0",
        "ai data center infrastructure",
        "cloud data center infrastructure",
        "scale-up infrastructure",
        "data center interconnect",
        "ethernet switch",
        "nvlink fusion",
        "optical performance",
        "3.2t",
        "custom silicon",
        "memory pooling",
        "ai memory wall",
        "connectivity silicon",
    ]

    # 产品名称
    PRODUCT_NAMES = [
        "blackwell", "rubin", "vera", "dgx", "drive",
        "cosmos", "jetson", "rtx", "hopper", "grace",
    ]

    # 供应链合作关键词
    SUPPLY_CHAIN_KEYWORDS = [
        "sk hynix", "tsmc", "foxconn", "memory",
        "semiconductor manufacturing", "fabs", "hbm",
        "advanced packaging", "foundry",
    ]

    # AMD 专属关键词
    AMD_AI_INVESTMENT_KEYWORDS = [
        "commits up to", "£", "accelerate ai innovation",
        "ai research", "uk",
    ]
    AMD_SUPPLY_CHAIN_INVESTMENT_KEYWORDS = [
        "taiwan ecosystem investments",
        "ecosystem investment", "taiwan",
        "ai ecosystem",
    ]
    AMD_AI_EVENT_KEYWORDS = [
        "advancing ai", "ai event", "keynote",
    ]
    AMD_AI_PC_KEYWORDS = [
        "ai pc", "ryzen", "ai pc options", "expanded ryzen",
    ]

    # 低价值关键词
    LOW_VALUE_KEYWORDS = [
        "geforce now", "summer sale", "games join",
        "gaming community", "stockholder meeting",
        "annual meeting", "participate online",
        "media contact", "investor relations contact",
        "forecast: fun ahead", "blog",
    ]

    # 高价值关键词（用于排除低价值误判）
    HIGH_VALUE_KEYWORDS = [
        "revenue", "financial results", "partnership",
        "collaboration", "ai factory", "full production",
        "blackwell", "rubin", "hbm", "data center",
        "cloud", "multiyear",
    ]

    # 投资者材料关键词
    INVESTOR_MATERIAL_KEYWORDS = [
        "investor presentation", "shareholder letter",
        "cfo commentary", "quarterly update",
        "investor day", "analyst day", "annual report",
    ]

    # 股东回报关键词
    CAPITAL_RETURN_KEYWORDS = [
        "share repurchase", "buyback", "stock repurchase", "share buyback",
        "repurchase program", "buyback authorization",
    ]

    # 股票分割关键词
    STOCK_SPLIT_KEYWORDS = [
        "stock split",
        "ten-to-one stock split",
        "10-for-1 stock split",
        "10-to-1 stock split",
        "forward stock split",
        "announces stock split",
    ]

    # 投资者活动预告关键词
    INVESTOR_EVENT_NOTICE_KEYWORDS = [
        "webcast details",
        "upcoming investor day",
        "upcoming investor webcast",
        "investor day webcast",
        "participate in upcoming conferences",
        "investor conferences",
        "to participate in",
        "will participate in",
    ]

    # 排除投资者活动的关键词（这些应该是更高价值的）
    INVESTOR_EVENT_EXCLUDE_KEYWORDS = [
        "financial results reported",
        "share repurchase",
        "buyback",
        "stock split",
        "acquisition",
        "partnership",
        "announces $",
        "billion",
    ]

    # 普通季度分红关键词
    REGULAR_DIVIDEND_KEYWORDS = [
        "declares quarterly dividend",
        "quarterly dividend payment",
        "regular quarterly dividend",
    ]

    # 特殊分红关键词（更高价值）
    SPECIAL_DIVIDEND_KEYWORDS = [
        "special dividend",
        "increases dividend",
        "raises dividend",
        "dividend increase",
        "new repurchase program",
        "authorizes buyback",
    ]

    # 高管变动关键词
    EXECUTIVE_CHANGE_KEYWORDS = [
        "cfo transition",
        "ceo transition",
        "chief financial officer",
        "chief executive officer",
        "appoints cfo",
        "appoints ceo",
        "names cfo",
        "names CEO",
        "new cfo",
        "new ceo",
    ]

    # 高管离职关键词（更高分）
    EXECUTIVE_DEPARTURE_KEYWORDS = [
        "resigns",
        "steps down",
        "departure",
        "effective immediately",
        "sudden",
    ]

    # 低优先级职位（不触发高分）
    LOW_PRIORITY_POSITIONS = [
        "board chair",
        "board member",
        "director",
        "legal officer",
        "chief legal officer",
        "people officer",
        "investor relations",
    ]

    # 业务更新关键词
    BUSINESS_UPDATE_KEYWORDS = [
        "acquisition", "expands", "announces new",
    ]

    # ========== Company-specific keywords ==========
    # AAPL
    AAPL_AI_PRODUCT_KEYWORDS = [
        "apple intelligence", "siri ai", "ai capabilities",
        "intelligence experiences", "on-device intelligence",
        "private cloud compute",
    ]
    AAPL_DMA_KEYWORDS = [
        "dma", "delayed in eu", "european union", "regulation",
    ]
    AAPL_DMA_PRODUCT_KEYWORDS = [
        "siri ai", "apple intelligence", "ios", "ipados",
    ]
    AAPL_APP_STORE_KEYWORDS = [
        "app store ecosystem", "reaches $", "trillion", "billion",
        "fraudulent transactions", "developers thrive", "transactions",
    ]
    AAPL_DEVELOPER_ACADEMY_KEYWORDS = [
        "developer academy", "rising developers", "education",
        "students", "community",
    ]
    AAPL_CONTENT_SERVICE_KEYWORDS = [
        "apple sports", "friday night baseball", "major league baseball",
        "apple arcade", "apple tv", "mini football", "family feud",
        "sports event", "live pro sports",
    ]
    AAPL_CONTENT_SERVICE_EXCLUDE_KEYWORDS = [
        "revenue", "subscribers", "paid users", "regulatory",
        "ai", "apple intelligence",
    ]
    AAPL_HIGH_VALUE_KEYWORDS = [
        "revenue", "acquisition", "ai", "app store ecosystem",
    ]

    # GOOGL
    GOOGL_AI_PRODUCT_KEYWORDS = [
        "gemini", "deepmind", "ai overviews", "tpu",
        "ai mode", "notebooklm", "search ai", "chrome ai",
        "workspace ai", "google ai studio",
    ]
    GOOGL_CLOUD_KEYWORDS = [
        "google cloud", "cloud revenue", "gcp",
    ]
    GOOGL_AUTONOMOUS_KEYWORDS = [
        "waymo", "self-driving", "autonomous driving",
    ]
    GOOGL_INFRASTRUCTURE_KEYWORDS = [
        "data center", "cloud infrastructure", "google cloud",
        "ai infrastructure", "capital investment", "new investments",
        "power", "grid", "clean energy", "cloud region",
        "tpu", "ai capacity", "alabama", "virginia",
    ]
    GOOGL_INFRASTRUCTURE_CONTEXT_KEYWORDS = [
        "investment", "jobs", "cloud", "ai", "infrastructure",
        "data center",
    ]
    GOOGL_AI_MODEL_KEYWORDS = [
        "gemma", "diffusiongemma", "imagen", "veo",
        "gemini model", "open model", "model release",
        "4x faster text generation",
    ]
    GOOGL_AD_PARTNERSHIP_KEYWORDS = [
        "walmart connect", "display & video 360", "ads",
        "marketing platform",
    ]
    GOOGL_LOW_VALUE_KEYWORDS = [
        "students", "parents", "digital literacy", "arts",
        "culture", "report", "teen voices", "future report",
        "commencement address",
    ]

    # MSFT
    MSFT_AI_PRODUCT_KEYWORDS = [
        "copilot", "ai pc", "windows ai", "openai",
    ]
    MSFT_CLOUD_KEYWORDS = [
        "azure", "cloud revenue", "azure ai",
    ]
    MSFT_INFRASTRUCTURE_KEYWORDS = [
        "data center", "ai infrastructure", "cloud infrastructure",
    ]

    # META
    META_METAVERSE_HARDWARE_KEYWORDS = [
        "ray-ban meta", "smart glasses", "ai glasses",
        "quest", "horizon", "reality labs",
        "wearable", "ar glasses", "vr headset",
    ]
    META_AI_INFRASTRUCTURE_KEYWORDS = [
        "data center", "ai-enabled data center", "compute power",
        "ai infrastructure", "gpu cluster", "training cluster",
        "power agreement", "energy agreement", "reliance",
    ]
    META_AI_PRODUCT_KEYWORDS = [
        "meta ai", "ai tools", "generative ai",
        "ai assistant", "ai translations", "llama",
        "facebook ai tools",
    ]
    META_REGULATORY_POLICY_KEYWORDS = [
        "social media bans", "age verification", "community standards",
        "enforcement report", "independent audit", "transparency report",
        "policy update", "comment on",
    ]
    META_SECURITY_UPDATE_KEYWORDS = [
        "spyware", "whatsapp security", "vulnerability",
        "cyber", "encryption", "malware",
    ]
    META_PRIVACY_POLICY_KEYWORDS = [
        "personalization", "controls", "activity",
        "privacy", "data controls", "ad preferences",
    ]
    META_SOCIAL_APP_KEYWORDS = [
        "threads", "facebook", "instagram",
        "reels", "creators", "football fans",
        "meta apps",
    ]
    META_WORKFORCE_TRAINING_KEYWORDS = [
        "workforce academy", "free skills", "training",
        "education", "veterans",
    ]

    def classify(self, item: dict) -> dict:
        """
        分类IR新闻

        Args:
            item: normalize后的新闻item

        Returns:
            更新后的item（包含document_type, event_hint, pre_score, need_ai）
        """
        title = (item.get('title', '') or '').lower()
        content = (item.get('content', '') or '').lower()
        summary = (item.get('summary', '') or '').lower()

        text = f"{title} {content} {summary}"

        ticker = item.get('ticker', '').upper()

        # ========== Company-specific rules (highest priority) ==========

        # AAPL rules
        if ticker == 'AAPL':
            # 1. DMA / EU delay (80) - higher priority than AI product
            if self._match_any(text, self.AAPL_DMA_KEYWORDS) and \
               self._match_any(text, self.AAPL_DMA_PRODUCT_KEYWORDS):
                return self._set_classification(item, 'regulatory_product_delay', 'regulatory_product_delay', 80, True)

            # 2. Apple Intelligence / Siri AI (75)
            if self._match_any(text, self.AAPL_AI_PRODUCT_KEYWORDS):
                return self._set_classification(item, 'ai_product_update', 'ai_product_update', 75, True)

            # 3. App Store metrics (70)
            if self._match_any(text, self.AAPL_APP_STORE_KEYWORDS):
                return self._set_classification(item, 'business_metric_update', 'business_metric_update', 70, True)

            # 4. Content service (50) - Apple Sports, Arcade, TV content
            if self._match_any(text, self.AAPL_CONTENT_SERVICE_KEYWORDS):
                # 检查是否有排除关键词（使用单词边界匹配，避免误判）
                has_exclude = False
                for kw in self.AAPL_CONTENT_SERVICE_EXCLUDE_KEYWORDS:
                    # 对于短关键词如 "ai"，使用单词边界匹配
                    if len(kw) <= 3:
                        import re
                        if re.search(r'\b' + re.escape(kw) + r'\b', text):
                            has_exclude = True
                            break
                    else:
                        if kw in text:
                            has_exclude = True
                            break

                if not has_exclude:
                    return self._set_classification(item, 'content_service_update', 'content_service_update', 50, False)

            # 5. Developer Academy (50, low priority)
            if self._match_any(text, self.AAPL_DEVELOPER_ACADEMY_KEYWORDS) and \
               not self._match_any(text, self.AAPL_HIGH_VALUE_KEYWORDS):
                return self._set_classification(item, 'developer_ecosystem', 'developer_ecosystem', 50, False)

        # GOOGL rules
        if ticker == 'GOOGL':
            # 1. Ad partnership (80)
            if self._match_any(text, self.GOOGL_AD_PARTNERSHIP_KEYWORDS):
                return self._set_classification(item, 'strategic_partnership', 'strategic_partnership', 80, True)

            # 2. Autonomous driving (80)
            if self._match_any(text, self.GOOGL_AUTONOMOUS_KEYWORDS):
                return self._set_classification(item, 'autonomous_driving', 'autonomous_driving', 80, True)

            # 3. AI infrastructure (75)
            if self._match_any(text, self.GOOGL_INFRASTRUCTURE_KEYWORDS) and \
               self._match_any(text, self.GOOGL_INFRASTRUCTURE_CONTEXT_KEYWORDS):
                return self._set_classification(item, 'ai_infrastructure', 'ai_infrastructure', 75, True)

            # 4. AI products (75)
            if self._match_any(text, self.GOOGL_AI_PRODUCT_KEYWORDS):
                return self._set_classification(item, 'ai_product_update', 'ai_product_update', 75, True)

            # 5. AI model update (65, no AI needed)
            if self._match_any(text, self.GOOGL_AI_MODEL_KEYWORDS):
                # 确认不涉及商业化/客户/云收入
                if not any(kw in text for kw in ['customer', 'revenue', 'cloud', 'commercial']):
                    return self._set_classification(item, 'ai_model_update', 'ai_model_update', 65, False)

            # 6. Cloud update (70)
            if self._match_any(text, self.GOOGL_CLOUD_KEYWORDS):
                return self._set_classification(item, 'cloud_update', 'cloud_update', 70, True)

            # 7. Education/culture/report (50)
            if self._match_any(text, self.GOOGL_LOW_VALUE_KEYWORDS):
                # 确认没有明显商业化/AI基础设施/云收入
                if not self._match_any(text, self.GOOGL_INFRASTRUCTURE_KEYWORDS) and \
                   not any(kw in text for kw in ['revenue', 'cloud revenue', 'ai infrastructure']):
                    return self._set_classification(item, 'company_news', 'company_news', 50, False)

            # AI infrastructure (75)
            if self._match_any(text, self.GOOGL_INFRASTRUCTURE_KEYWORDS):
                return self._set_classification(item, 'ai_infrastructure', 'ai_infrastructure', 75, True)

        # MSFT rules
        if ticker == 'MSFT':
            # AI products (75)
            if self._match_any(text, self.MSFT_AI_PRODUCT_KEYWORDS):
                return self._set_classification(item, 'ai_product_update', 'ai_product_update', 75, True)

            # Cloud update (70)
            if self._match_any(text, self.MSFT_CLOUD_KEYWORDS):
                return self._set_classification(item, 'cloud_update', 'cloud_update', 70, True)

            # AI infrastructure (75) - but skip if it's a strategic partnership announcement
            if self._match_any(text, self.MSFT_INFRASTRUCTURE_KEYWORDS) and \
               not self._match_any(text, self.STRATEGIC_PARTNERSHIP_KEYWORDS):
                return self._set_classification(item, 'ai_infrastructure', 'ai_infrastructure', 75, True)

        # META rules
        if ticker == 'META':
            # 1. Metaverse hardware (75, need_ai=True) - 只限智能眼镜/Quest/VR
            if self._match_any(text, self.META_METAVERSE_HARDWARE_KEYWORDS):
                return self._set_classification(item, 'metaverse_hardware', 'metaverse_hardware', 75, True)

            # 2. AI infrastructure (80, need_ai=True) - data center/compute power
            if self._match_any(text, self.META_AI_INFRASTRUCTURE_KEYWORDS):
                return self._set_classification(item, 'ai_infrastructure', 'ai_infrastructure', 80, True)

            # 3. AI product update (75, need_ai=True) - Meta AI/AI tools/Llama
            if self._match_any(text, self.META_AI_PRODUCT_KEYWORDS):
                return self._set_classification(item, 'ai_product_update', 'ai_product_update', 75, True)

            # 4. Regulatory policy (50, need_ai=False)
            if self._match_any(text, self.META_REGULATORY_POLICY_KEYWORDS):
                return self._set_classification(item, 'regulatory_policy', 'regulatory_policy', 50, False)

            # 5. Security update (60, need_ai=False)
            if self._match_any(text, self.META_SECURITY_UPDATE_KEYWORDS):
                return self._set_classification(item, 'security_update', 'security_update', 60, False)

            # 6. Privacy policy update (50, need_ai=False)
            if self._match_any(text, self.META_PRIVACY_POLICY_KEYWORDS):
                return self._set_classification(item, 'privacy_policy_update', 'privacy_policy_update', 50, False)

            # 7. Social app update (50, need_ai=False) - Threads/Facebook/Instagram
            if self._match_any(text, self.META_SOCIAL_APP_KEYWORDS):
                # 确认没有AI/data center/glasses等强关键词
                if not self._match_any(text, self.META_AI_PRODUCT_KEYWORDS) and \
                   not self._match_any(text, self.META_AI_INFRASTRUCTURE_KEYWORDS) and \
                   not self._match_any(text, self.META_METAVERSE_HARDWARE_KEYWORDS):
                    return self._set_classification(item, 'social_app_update', 'social_app_update', 50, False)

            # 8. Workforce training / education (50, need_ai=False)
            if self._match_any(text, self.META_WORKFORCE_TRAINING_KEYWORDS):
                # 确认没有AI infrastructure/product/monetization
                if not self._match_any(text, self.META_AI_INFRASTRUCTURE_KEYWORDS) and \
                   not self._match_any(text, self.META_AI_PRODUCT_KEYWORDS):
                    return self._set_classification(item, 'company_news', 'company_news', 50, False)

        # AMD rules
        if ticker == 'AMD':
            # 1. Supply chain investment (80, need_ai=True) - $10B Taiwan ecosystem (优先级最高，避免被AI investment拦截)
            if self._match_any(text, self.AMD_SUPPLY_CHAIN_INVESTMENT_KEYWORDS):
                return self._set_classification(item, 'supply_chain_investment', 'supply_chain_investment', 80, True)

            # 2. AI investment (80, need_ai=True) - £2B UK AI innovation
            if self._match_any(text, self.AMD_AI_INVESTMENT_KEYWORDS):
                return self._set_classification(item, 'ai_investment', 'ai_investment', 80, True)

            # 3. AI event notice (60, need_ai=False) - Advancing AI 2026
            if self._match_any(text, self.AMD_AI_EVENT_KEYWORDS):
                return self._set_classification(item, 'investor_event_notice', 'ai_event_notice', 60, False)

            # 4. AI PC product (65, need_ai=False) - Ryzen AI PC
            if self._match_any(text, self.AMD_AI_PC_KEYWORDS):
                return self._set_classification(item, 'ai_pc_product_update', 'ai_pc_product_update', 65, False)

        # ========== Generic rules (lower priority) ==========

        # 1. 财报日期预告（65分）- 最优先判断
        if self._match_any(text, self.EARNINGS_EVENT_KEYWORDS):
            # 确认不包含实际财务数字（排除误判）
            if not self._match_any(text, self.ACTUAL_FINANCIAL_KEYWORDS):
                # 检查是否包含guidance等需要AI分析的内容
                needs_ai = self._match_any(text, self.EARNINGS_NOTICE_NEEDS_AI_KEYWORDS)
                return self._set_classification(item, 'earnings_event_notice', 'earnings_date_announcement', 65, needs_ai)

        # 2. 财报新闻稿（90分）- 在预告之后判断
        if self._match_any(text, self.EARNINGS_RELEASE_KEYWORDS):
            return self._set_classification(item, 'earnings_release', 'earnings_release', 90, True)

        # 3. 股票分割（75分）- 优先于高管变动和分红
        if self._match_any(text, self.STOCK_SPLIT_KEYWORDS):
            return self._set_classification(item, 'stock_split', 'stock_split', 75, True)

        # 4. 高管变动（75-85分）
        if self._match_any(text, self.EXECUTIVE_CHANGE_KEYWORDS):
            # 排除低优先级职位
            if not self._match_any(text, self.LOW_PRIORITY_POSITIONS):
                # 如果是突发离职，评分更高
                if self._match_any(text, self.EXECUTIVE_DEPARTURE_KEYWORDS):
                    return self._set_classification(item, 'executive_change', 'executive_change', 85, True)
                else:
                    return self._set_classification(item, 'executive_change', 'executive_change', 75, True)

        # 5. AI数据中心互连产品发布（85分）- 优先于供应链
        if self._match_any(text, self.AI_INTERCONNECT_KEYWORDS):
            # 如果同时有发布关键词，评分更高
            if self._match_any(text, self.PRODUCT_LAUNCH_KEYWORDS):
                return self._set_classification(item, 'product_launch', 'product_launch', 85, True)
            else:
                return self._set_classification(item, 'ai_infrastructure', 'ai_infrastructure', 80, True)

        # 5. 供应链合作（85分）
        if self._match_any(text, self.SUPPLY_CHAIN_KEYWORDS):
            return self._set_classification(item, 'supply_chain_partnership', 'supply_chain_partnership', 85, True)

        # 6. 产品量产（85分）
        if self._match_any(text, self.PRODUCT_RAMP_KEYWORDS) and \
           self._match_any(text, self.PRODUCT_NAMES):
            return self._set_classification(item, 'product_ramp', 'product_ramp', 85, True)

        # 5. AI基础设施（80分）- 优先于战略合作
        if self._match_any(text, self.AI_INFRASTRUCTURE_KEYWORDS):
            return self._set_classification(item, 'ai_infrastructure', 'ai_infrastructure', 80, True)

        # 6. 战略合作（80分）
        if self._match_any(text, self.STRATEGIC_PARTNERSHIP_KEYWORDS):
            return self._set_classification(item, 'strategic_partnership', 'strategic_partnership', 80, True)

        # 7. 投资者材料（80分）
        if self._match_any(text, self.INVESTOR_MATERIAL_KEYWORDS):
            # 排除投资者活动预告（优先级更低）
            if not self._match_any(text, self.INVESTOR_EVENT_NOTICE_KEYWORDS):
                return self._set_classification(item, 'investor_material', 'business_update', 80, True)

        # 8. 普通季度分红（60分，不需要AI）
        if self._match_any(text, self.REGULAR_DIVIDEND_KEYWORDS):
            # 确认不是特殊分红或回购
            if not self._match_any(text, self.SPECIAL_DIVIDEND_KEYWORDS) and \
               not self._match_any(text, self.CAPITAL_RETURN_KEYWORDS):
                return self._set_classification(item, 'capital_return', 'regular_dividend', 60, False)

        # 9. 股东回报/特殊分红（80分）
        if self._match_any(text, self.CAPITAL_RETURN_KEYWORDS) or \
           self._match_any(text, self.SPECIAL_DIVIDEND_KEYWORDS):
            return self._set_classification(item, 'capital_return', 'capital_return', 80, True)

        # 10. 投资者活动预告（60分，不需要AI）
        if self._match_any(text, self.INVESTOR_EVENT_NOTICE_KEYWORDS):
            # 确认不是更高价值的业务公告
            if not self._match_any(text, self.INVESTOR_EVENT_EXCLUDE_KEYWORDS):
                return self._set_classification(item, 'investor_event_notice', 'investor_event_notice', 60, False)

        # 11. 低价值（30分）
        if self._match_any(text, self.LOW_VALUE_KEYWORDS) and \
           not self._match_any(text, self.HIGH_VALUE_KEYWORDS):
            return self._set_classification(item, 'low_value_company_news', 'low_value_company_news', 30, False)

        # 12. 业务更新（75分）
        if self._match_any(text, self.BUSINESS_UPDATE_KEYWORDS):
            # 排除投资者活动预告
            if not self._match_any(text, self.INVESTOR_EVENT_NOTICE_KEYWORDS):
                # 排除 AAPL content service
                if ticker == 'AAPL' and self._match_any(text, self.AAPL_CONTENT_SERVICE_KEYWORDS):
                    # 这是content service，不是business update
                    pass
                else:
                    return self._set_classification(item, 'press_release', 'business_update', 75, True)

        # 13. 默认（50分）
        return self._set_classification(item, 'press_release', 'company_news', 50, False)

    def _set_classification(
        self,
        item: dict,
        document_type: str,
        event_hint: str,
        pre_score: int,
        need_ai: bool
    ) -> dict:
        """设置分类结果"""
        item['document_type'] = document_type
        item['event_hint'] = event_hint
        item['pre_score'] = pre_score

        # need_ai统一后处理：使用 _should_need_ai 强制规则
        item['need_ai'] = self._should_need_ai(event_hint, pre_score, need_ai)

        return item

    def _should_need_ai(self, event_hint: str, pre_score: int, suggested_need_ai: bool) -> bool:
        """
        统一判断是否需要AI分析

        Args:
            event_hint: 事件提示
            pre_score: 预评分
            suggested_need_ai: 规则建议的need_ai值

        Returns:
            最终的need_ai值
        """
        # 强制 False 的事件类型
        force_false = [
            'company_news',
            'low_value_company_news',
            'developer_ecosystem',
            'content_service_update',
            'social_app_update',
            'ai_model_update',
            'ai_pc_product_update',
            'investor_event_notice',
            'ai_event_notice',
            'regular_dividend',
            'regulatory_policy',
            'security_update',
            'privacy_policy_update',
            'workforce_training',
        ]

        if event_hint in force_false:
            return False

        # 强制 True 的事件类型
        force_true = [
            'earnings_release',
            'executive_change',
            'strategic_partnership',
            'product_launch',
            'product_ramp',
            'ai_infrastructure',
            'ai_investment',
            'supply_chain_investment',
            'supply_chain_partnership',
            'business_metric_update',
            'regulatory_product_delay',
            'ai_product_update',
            'metaverse_hardware',
        ]

        if event_hint in force_true:
            return True

        # earnings_date_announcement 使用 suggested_need_ai（动态判断）
        if event_hint == 'earnings_date_announcement':
            return suggested_need_ai

        # 其他事件类型根据 pre_score
        if pre_score >= 65:
            return True

        return False

    def _match_any(self, text: str, keywords: list[str]) -> bool:
        """检查文本是否匹配任意关键词"""
        return any(keyword in text for keyword in keywords)


__all__ = ['IRRules']
