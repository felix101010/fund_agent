"""
CLS Pipeline集成补丁
在single_news_pipeline.py的AI抽取后增加标题公司名识别和付费标题检测
"""

# ============================================================================
# 在 SingleNewsPipeline.__init__() 中增加
# ============================================================================

from fund_quant.nlp.entity_linking import TitleCompanyExtractor, StockEntityResolver
from fund_quant.nlp.news_filter.paid_content_detector import PaidContentDetector

def __init__(self, ai_extractor: AIEventExtractor = None):
    """初始化"""
    self.rule_filter = SimpleRuleFilter()
    self.unknown_filter = UnknownDecisionFilter()
    self.ai_extractor = ai_extractor or AIEventExtractor()
    
    # 新增：标题公司名识别和付费内容检测
    self.title_extractor = TitleCompanyExtractor()
    self.stock_resolver = StockEntityResolver()
    self.paid_detector = PaidContentDetector()


# ============================================================================
# 在 AI抽取后、返回前增加（大约第110-120行之间）
# ============================================================================

# 4. AI事件抽取
ai_event = self.ai_extractor.extract(news)
result.ai_event = ai_event

# 5. 新增：标题公司名识别和付费内容检测
try:
    # 5.1 提取标题中的公司名
    title = result.title
    content = result.content
    
    candidates = self.title_extractor.extract(title)
    
    # 5.2 解析公司名到股票代码
    title_stocks = []
    for candidate in candidates:
        resolved = self.stock_resolver.resolve_company_name(candidate.name)
        if resolved:
            title_stocks.append({
                'name': resolved['name'],
                'code': resolved['code'],
                'match_source': 'title_rule',
                'match_confidence': resolved['match_confidence']
            })
    
    # 5.3 合并AI抽取的股票和标题识别的股票
    if title_stocks and ai_event and hasattr(ai_event, 'related_stocks'):
        # 获取AI的related_stocks
        ai_stocks = getattr(ai_event, 'related_stocks', [])
        
        # 按code去重合并
        all_stocks = {}
        
        # 先加入标题识别的（优先级高）
        for stock in title_stocks:
            code = stock.get('code')
            if code:
                all_stocks[code] = stock
        
        # 再加入AI的（如果code不冲突）
        for stock in ai_stocks:
            code = getattr(stock, 'code', None) if hasattr(stock, 'code') else stock.get('code')
            name = getattr(stock, 'name', None) if hasattr(stock, 'name') else stock.get('name')
            if code and code not in all_stocks:
                all_stocks[code] = {
                    'name': name,
                    'code': code,
                    'match_source': 'ai_extraction',
                    'match_confidence': 0.7
                }
        
        # 更新ai_event.related_stocks
        if hasattr(ai_event, 'related_stocks'):
            ai_event.related_stocks = list(all_stocks.values())
    
    # 5.4 付费内容检测
    paid_result = self.paid_detector.detect(title, content)
    result.paid_content_result = paid_result
    
    # 5.5 付费标题限分
    if paid_result.is_paid_locked and ai_event:
        # 获取related_stocks数量
        related_stocks = getattr(ai_event, 'related_stocks', [])
        related_stocks_count = len(related_stocks) if related_stocks else 0
        
        if paid_result.stock_visibility == "hidden_by_paid_content":
            # 规则1: paid_locked + hidden_stock
            if hasattr(ai_event, 'event_type'):
                ai_event.event_type = "research_teaser"
            if hasattr(ai_event, 'related_stocks'):
                ai_event.related_stocks = []
            if hasattr(ai_event, 'final_score'):
                ai_event.final_score = min(getattr(ai_event, 'final_score', 100), 60)
            if hasattr(ai_event, 'trade_priority'):
                ai_event.trade_priority = "watch"
            if hasattr(ai_event, 'confidence'):
                ai_event.confidence = min(getattr(ai_event, 'confidence', 1.0), 0.55)
            
            # 更新error_tags
            if not hasattr(result, 'error_tags'):
                result.error_tags = []
            result.error_tags.extend([
                'paid_locked',
                'title_only_signal',
                'stock_hidden_by_paid_content',
                'score_capped_by_paid_lock'
            ])
            
        elif related_stocks_count > 0:
            # 规则2: paid_locked但有可见股票
            if hasattr(ai_event, 'final_score'):
                ai_event.final_score = min(getattr(ai_event, 'final_score', 100), 65)
            if hasattr(ai_event, 'trade_priority'):
                priority = getattr(ai_event, 'trade_priority', 'watch')
                if priority in ['high', 'urgent']:
                    ai_event.trade_priority = 'candidate'
            if hasattr(ai_event, 'confidence'):
                ai_event.confidence = min(getattr(ai_event, 'confidence', 1.0), 0.65)
            
            if not hasattr(result, 'error_tags'):
                result.error_tags = []
            result.error_tags.extend([
                'paid_locked',
                'title_only_signal',
                'score_capped_by_paid_lock'
            ])
    
    # 5.6 高分无股票限分
    if ai_event:
        final_score = getattr(ai_event, 'final_score', 0)
        related_stocks = getattr(ai_event, 'related_stocks', [])
        related_stocks_count = len(related_stocks) if related_stocks else 0
        event_type = getattr(ai_event, 'event_type', '')
        
        # 宏观政策/大宗商品例外
        exempted_types = ['macro_policy', 'major_policy', 'commodity_price_increase', 'geopolitical_supply_risk']
        
        if final_score >= 70 and related_stocks_count == 0 and event_type not in exempted_types:
            # 限分
            ai_event.final_score = min(final_score, 65)
            if hasattr(ai_event, 'trade_priority'):
                priority = getattr(ai_event, 'trade_priority', 'watch')
                if priority in ['high', 'urgent']:
                    ai_event.trade_priority = 'candidate'
            if hasattr(ai_event, 'confidence'):
                ai_event.confidence = min(getattr(ai_event, 'confidence', 1.0), 0.65)
            
            if not hasattr(result, 'error_tags'):
                result.error_tags = []
            if 'score_capped_no_stock' not in result.error_tags:
                result.error_tags.append('score_capped_no_stock')

except Exception as e:
    # 标题公司名识别失败不中断pipeline
    if not hasattr(result, 'error_tags'):
        result.error_tags = []
    result.error_tags.append('title_company_extraction_failed')
    result.postprocess_notes = result.postprocess_notes or []
    result.postprocess_notes.append(f"标题公司名识别失败: {str(e)}")

# 记录后处理注释
result.processing_status = "success"

