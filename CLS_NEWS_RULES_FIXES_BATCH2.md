# CLS 新闻规则修复 - 第二批增强

**日期**: 2026-06-17  
**状态**: ✅ 全部完成，31个测试通过

## 本次修复的6个问题

### 1. ✅ 扩大付费研报识别

**修改文件**: `src/fund_quant/nlp/news_filter/paid_content_detector.py`

**新增关键词**:
- 研选、研报数据、研选•研报数据
- 机构称、分析师强call
- 公司晋身、充分受益、迎共振式增长
- 拟受益、有望受益

**新增主题识别**:
- 磷化铟 (InP)
- Low-Dk材料、二代布
- 光芯片需求

**效果**:
```
【研选•研报数据】AI持续拉动光芯片需求，关键材料体系磷化铟...
✅ 识别为 paid_research_teaser
✅ theme_ids: [ai_compute, optical_module, semiconductor_material, inp, low_dk_material]
✅ supply_chain_position: AI光芯片与高速材料
```

### 2. ✅ 增强战争无人机修正

**修改文件**: `src/fund_quant/nlp/news_filter/keyword_rules.py`

**扩大战争关键词**:
- 乌军、俄军、白俄罗斯
- 恐袭、打击、战斗
- 防空系统
- 攻击型无人机、固定翼无人机

**新增能源关键词**:
- 油轮、天然气

**效果**:
```
俄侦委以恐袭立案调查白俄罗斯少年球队客车遇袭事件
乌军使用攻击型无人机袭击俄罗斯公路客车

✅ 不再误判为 low_altitude_economy
✅ event_type = geopolitical_risk
✅ ai_level = none
✅ risk_flags 包含 war_drone_not_low_altitude
```

### 3. ✅ 海外AI合作/软件/液冷映射

**修改文件**: `src/fund_quant/nlp/news_filter/keyword_rules.py`

**新增功能**: 重写 `classify_overseas_ai_infrastructure`，支持三类：

#### A. AI 软件（Copilot/DeepSeek）

**新增关键词**:
- Copilot、DeepSeek
- 协同工作平台、协作功能
- AI助手、Microsoft 365、Office AI

**效果**:
```
微软据称考虑将DeepSeek用于Copilot协同工作平台
✅ primary_theme_id = ai_software
✅ event_type = ai_product_update
✅ ai_level = light

微软表示，Copilot协作功能现已全面推出
✅ primary_theme_id = ai_software
```

#### B. 企业AI合作

**新增关键词**:
- 代理式人工智能、agentic AI
- 引入生产环境、enterprise AI
- 慧与科技、HPE、惠普企业

**效果**:
```
慧与科技携手英伟达将代理式人工智能引入生产环境
✅ primary_theme_id = ai_compute
✅ event_type = enterprise_ai_cooperation
✅ ai_level = light
```

#### C. 液冷系统

**新增关键词**:
- Brazos液冷系统
- 数据中心冷却、thermal management

**效果**:
```
谷歌推出用于数据中心的Brazos液冷系统
✅ primary_theme_id = ai_compute
✅ event_type = ai_infrastructure_product
✅ theme_ids 包含 liquid_cooling
```

### 4. ✅ 苹果AI终端主题修正

**修改文件**: `src/fund_quant/nlp/news_filter/keyword_rules.py`

**新增函数**: `classify_apple_ai_terminal(item)`

**识别关键词**:
- AirPods、摄像头AirPods
- 折叠iPhone、折叠手机、折叠屏
- AI可穿戴、计算机视觉

**效果**:
```
苹果计划2027年将推出带摄像头AirPods与新一代折叠iPhone

✅ primary_theme_id = consumer_electronics (不再是 semiconductor_material)
✅ event_type = ai_terminal_product
✅ theme_ids = [consumer_electronics, ai_terminal, ai_wearable, foldable_phone]
✅ final_score = 65
```

### 5. ✅ general低分无主题不需AI

**修改文件**: `src/fund_quant/nlp/news_filter/keyword_rules.py`

**增强函数**: `apply_ai_level(item)`

**新增逻辑**:

```python
# general + 低分 + 无主题 + 无股票
if event_type == 'general' and final_score < 50 and not primary_theme_id and related_stocks_count == 0:
    # 检查强AI关键词
    if has_strong_ai_keywords:
        ai_level = 'light'  # 给light但至少45分
        final_score = max(45, final_score)
        trade_priority = 'watch'
    else:
        ai_level = 'none'  # 纯general，archive
        trade_priority = 'archive'
```

**强AI关键词**:
- 英伟达、NVIDIA、OpenAI、谷歌、微软
- DeepSeek、Copilot、数据中心、AI工厂
- GPU、半导体、光模块、HBM

**效果**:

```
高盛2026年并购业务突破1万亿美元
✅ ai_level = none
✅ need_ai = False
✅ trade_priority = archive

微软据悉曾就租赁甲骨文云资源事宜进行谈判
✅ ai_level = light (有微软关键词)
✅ final_score >= 45
✅ trade_priority = watch
```

### 6. ✅ normalized_title 已在第一批完成

**功能**: 在 `cls_api_collector.py` 中已实现

**使用**: 所有规则函数都使用 `normalized_title` 进行匹配

## 测试覆盖

**测试文件**: `tests/test_cls_news_rule_fixes.py`

**测试数量**: 31个测试，全部通过 ✅

### 第一批测试（22个）

- ✅ normalized_title 生成 (3)
- ✅ 股票代码提取 (5)
- ✅ 付费研报基础 (3)
- ✅ 海外AI基建 (3)
- ✅ 战争无人机 (3)
- ✅ ai_level分级 (5)

### 第二批新增测试（9个）

1. ✅ `test_paid_teaser_extended` - 研选•研报数据
2. ✅ `test_war_drone_bus_attack` - 恐袭无人机袭击客车
3. ✅ `test_hpe_nvidia_enterprise_ai` - 慧与+英伟达企业AI
4. ✅ `test_microsoft_copilot_deepseek` - 微软Copilot+DeepSeek
5. ✅ `test_microsoft_copilot_release` - Copilot功能推出
6. ✅ `test_apple_airpods_foldable_iphone` - 苹果AI终端
7. ✅ `test_general_low_score_archive` - general低分archive
8. ✅ `test_general_low_score_with_ai_keywords` - general有AI关键词
9. ✅ `test_normalized_title_print` - normalized_title打印

## 修改的文件总结

### 仅修改3个文件（最小侵入）

1. **cls_api_collector.py** - 添加 `build_normalized_title()` 函数（第一批已完成）
2. **paid_content_detector.py** - 扩大关键词、增强主题提取
3. **keyword_rules.py** - 添加/增强4个函数：
   - `extract_stocks_by_code_pattern()` - 股票代码（第一批）
   - `classify_overseas_ai_infrastructure()` - 海外AI（增强）
   - `classify_apple_ai_terminal()` - 苹果AI终端（新增）
   - `fix_war_drone_theme()` - 战争无人机（增强）
   - `apply_ai_level()` - AI分级（增强）

4. **test_cls_news_rule_fixes.py** - 唯一的测试文件

## 集成建议（处理顺序）

```python
def process_cls_news(item: dict) -> dict:
    """处理单条 CLS 新闻"""
    
    # 1. 构建 normalized_title（已自动完成）
    
    # 2. 构建完整文本
    text = f"{item['normalized_title']} {item['title']} {item['content']}"
    
    # 3. 股票代码硬解析
    rule_stocks = extract_stocks_by_code_pattern(text)
    item['related_stocks'] = rule_stocks
    item['related_stocks_count'] = len(rule_stocks)
    
    # 4. 付费研报检测
    if is_paid_research_teaser(text):
        item = classify_paid_research_teaser(item)
        item = apply_ai_level(item)
        return item
    
    # 5. 苹果AI终端
    apple_result = classify_apple_ai_terminal(item)
    if apple_result:
        item.update(apple_result)
    
    # 6. 海外AI（基建/软件/液冷）
    ai_result = classify_overseas_ai_infrastructure(item)
    if ai_result:
        item.update(ai_result)
    
    # 7. 现有规则过滤
    # ... 原有 rule_filter 逻辑 ...
    
    # 8. AI 处理（如果 need_ai=True）
    # ... 原有 AI 逻辑 ...
    # 注意：AI 不能删除规则层的 related_stocks
    
    # 9. 战争无人机修正（后处理）
    item = fix_war_drone_theme(item)
    
    # 10. ai_level 计算（最后）
    item = apply_ai_level(item)
    
    # 11. 更新 related_stocks_count
    item['related_stocks_count'] = len(item.get('related_stocks', []))
    
    return item
```

## 验收结果

### 测试通过率

```
======================== 31 passed, 1 warning in 0.45s =========================
```

**100% 通过** ✅

### 解决的错例

| 错例类型 | 修复前 | 修复后 |
|---------|--------|--------|
| 【研选•研报数据】 | general | paid_research_teaser ✅ |
| 恐袭无人机袭击客车 | low_altitude_economy | geopolitical_risk ✅ |
| 慧与+英伟达企业AI | general, theme_missing | ai_compute, enterprise_ai_cooperation ✅ |
| 微软Copilot+DeepSeek | general, theme_missing | ai_software, ai_product_update ✅ |
| 苹果AirPods折叠iPhone | semiconductor_material | consumer_electronics, ai_terminal ✅ |
| 高盛并购业务 | need_ai=True | ai_level=none, archive ✅ |

## 核心改进

### 1. 主题覆盖更全面

- ✅ AI软件（Copilot/DeepSeek）
- ✅ 企业AI合作（代理式AI）
- ✅ 消费电子AI终端
- ✅ 磷化铟、Low-Dk材料
- ✅ 液冷系统

### 2. 付费研报识别更宽

关键词从12个扩展到25个，覆盖更多卖关子标题

### 3. 战争无人机识别更准

关键词扩展，包括恐袭、乌军、白俄罗斯等

### 4. AI资源使用更精准

general低分无主题不再浪费AI资源，但保留强AI关键词新闻

### 5. 苹果产品主题修正

AirPods/折叠iPhone映射到消费电子，不再误判为半导体材料

## 下一步

1. **集成到实际pipeline** - 按照集成建议调用这些函数
2. **实际数据验证** - 运行真实CLS数据测试效果
3. **监控错例** - 持续收集新的错例优化规则
4. **主题词库扩展** - 根据实际情况补充更多主题关键词

所有功能已完成，测试通过，可以集成！🚀
