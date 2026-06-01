# 主题ETF映射汇总报告

生成时间: 2026-06-01

## 架构调整

### 核心原则
- **主题分析指数（primary_index）**: 用于判断方向、计算主题强度
- **ETF跟踪指数（tracking_index）**: 用于交易执行
- **解耦策略**: 不要求ETF跟踪指数与主题分析指数完全一致，只要高度相关即可

### 匹配逻辑
1. **精确匹配**: ETF跟踪指数代码 == primary_index_code
2. **代码匹配**: ETF跟踪指数代码在acceptable_tracking_indices列表中
3. **关键词匹配**: ETF benchmark包含acceptable_tracking_indices中的关键词

### 匹配关系类型
- `same_as_primary`: ETF跟踪指数与主题分析指数相同
- `accepted_alternative`: ETF跟踪相关指数，通过acceptable_tracking_indices验证
- `manual_accepted`: 手动添加的映射
- `rejected`: 不匹配

## 匹配结果统计

### 总体情况
- **总主题数**: 22个
- **有候选ETF的主题**: 21个（95.5%）
- **无候选ETF的主题**: 1个（storage储能）
- **候选ETF总数**: 668只

### 按主题统计

| 主题ID | 主题名称 | 主题分析指数 | 候选ETF数量 | 状态 |
|--------|---------|-------------|-----------|------|
| finance | 金融 | 000934.SH | 207 | ✓ |
| dividend | 红利 | 000922.CSI | 84 | ✓ |
| healthcare | 医药 | 000933.SH | 59 | ✓ |
| consumer | 消费 | 000932.SH | 47 | ✓ |
| ai | 人工智能 | 931071.CSI | 35 | ✓ |
| chip | 芯片 | H30007.CSI | 30 | ✓ |
| pharma | 创新药 | 931152.CSI | 28 | ✓ |
| metal | 有色金属 | 000819.SH | 22 | ✓ |
| battery | 电池 | 881281.WI | 19 | ✓ |
| compute | 算力基础设施 | 931865.CSI | 19 | ✓ |
| semiconductor | 半导体 | H30184.CSI | 19 | ✓ |
| ev | 新能源车 | 399417.SZ | 18 | ✓ |
| solar | 光伏 | 931151.CSI | 16 | ✓ |
| hktech | 港股科技 | HSTECH.HI | 14 | ✓ |
| robot | 机器人 | H30590.CSI | 13 | ✓ |
| defense | 军工 | 399967.SZ | 12 | ✓ |
| consumer_electronics | 消费电子 | 931494.CSI | 8 | ✓ |
| satellite | 卫星产业 | 931594.CSI | 6 | ✓ |
| medtech | 医疗器械 | 931464.CSI | 5 | ✓ |
| power_grid | 电网设备 | 931663.CSI | 4 | ✓ |
| liquor | 白酒 | 399997.SZ | 3 | ✓ |
| storage | 储能 | 931746.CSI | 0 | ✗ |

## 当前问题

### 1. 流动性数据缺失
- **问题**: daily_bars表中只有33只ETF的历史数据
- **影响**: 无法计算668只候选ETF的流动性指标
- **结果**: 所有主题ETF池为空（除了1只在数据库中的ETF）

### 2. 主题指数数据缺失
- **问题**: 部分主题分析指数在Tushare中不存在
  - H30007.CSI（中华芯片指数）
  - H30184.CSI（中华半导体指数）
  - H30590.CSI（中华机器人指数）
  - 881281.WI（电池指数）
  - 931464.CSI（医疗器械指数）
  - HSTECH.HI（恒生科技指数）
- **影响**: 无法采集这些指数的历史数据用于主题强度分析

### 3. 配置问题
- **power_grid（电网设备）**: 配置的931663.CSI实际是"SHS消费龙头"，不是电网设备指数

## 下一步工作

### Phase 1: 数据采集（优先级P0）

#### 1.1 采集主题ETF历史数据
```bash
# 从theme_etf_candidates.csv中选择需要采集的ETF
# 建议策略：
# - 每个主题选择Top 5-10只（按上市时间、规模筛选）
# - 优先采集主流基金公司的ETF
# - 总计约100-150只ETF
```

#### 1.2 采集主题分析指数数据
```bash
# 优先采集能找到的指数：
# - 931071.CSI（人工智能）
# - 931494.CSI（消费电子）
# - 931865.CSI（算力）
# - 399417.SZ（新能源车）
# - 931151.CSI（光伏）
# - 931746.CSI（储能）
# - 931152.CSI（创新药）
# - 000933.SH（医药）
# - 399967.SZ（军工）
# - 000932.SH（消费）
# - 399997.SZ（白酒）
# - 000934.SH（金融）
# - 000922.CSI（红利）
# - 000819.SH（有色金属）
```

#### 1.3 解决缺失指数问题
- **H30007/H30184/H30590**: 查找中华指数系列的数据源
- **881281.WI**: 查找Wind指数数据源或替代指数
- **931464.CSI**: 确认指数代码是否正确
- **HSTECH.HI**: 从港交所或其他数据源获取
- **931663.CSI**: 重新确认电网设备的正确指数代码

### Phase 2: 配置优化（优先级P1）

#### 2.1 优化acceptable_tracking_indices
- 根据实际匹配结果，调整关键词
- 避免过度匹配（如compute匹配到所有半导体ETF）
- 添加排除规则

#### 2.2 修正错误配置
- power_grid: 找到正确的电网设备指数

#### 2.3 补充storage主题
- 添加"储能"关键词到acceptable_tracking_indices
- 或手动添加储能相关ETF

### Phase 3: 流动性筛选（优先级P1）

#### 3.1 设置合理的流动性阈值
```python
# 当前阈值：
min_avg_amount_20d = 10,000,000  # 1000万

# 建议分级：
# - 高流动性: >= 5000万（主力交易）
# - 中流动性: >= 1000万（备选）
# - 低流动性: >= 500万（观察）
```

#### 3.2 每个主题保留Top N
```python
# 当前: top_n = 3
# 建议: top_n = 5（增加备选）
```

### Phase 4: 验证和测试（优先级P2）

#### 4.1 验证匹配准确性
- 人工抽查每个主题的Top 5 ETF
- 确认ETF确实与主题高度相关

#### 4.2 回测流动性筛选
- 使用历史数据验证流动性阈值是否合理
- 检查是否有流动性突然下降的ETF

## 输出文件

### 1. theme_etf_candidates.csv
- **路径**: `data/processed/theme_etf_candidates.csv`
- **内容**: 668只候选ETF的完整清单
- **字段**: theme_id, theme_name, primary_index_code, etf_code, etf_name, benchmark, match_type, list_date

### 2. theme_etf_pool.csv
- **路径**: `data/processed/theme_etf_pool.csv`
- **内容**: 经过流动性筛选后的最终ETF池（当前为空）
- **字段**: theme, theme_name, primary_index_code, etf_code, etf_name, tracking_index_code, tracking_index_relation, liquidity_metrics, rank_in_theme

### 3. theme_etf_pool_report.csv
- **路径**: `data/processed/theme_etf_pool_report.csv`
- **内容**: 每个主题的匹配统计报告
- **字段**: theme, theme_name, primary_index_code, matched_etf_count, selected_etf_count, best_etf, status, warning

## 技术实现

### 配置文件结构
```yaml
# configs/themes/theme_index_mapping.yaml
mappings:
  - theme_id: metal
    theme_name: 有色金属
    primary_index:
      code: 000819.SH
      name: 中证有色金属指数
    acceptable_tracking_indices:
      - 000819.SH              # 精确匹配
      - 有色金属                # 关键词匹配
      - 有色                   # 关键词匹配
```

### 匹配函数
```python
def match_etf_to_theme(etf_row, theme, index_mapping):
    tracking_code = etf_row['tracking_index_code']
    primary_code = theme['primary_index_code']
    acceptable = theme['acceptable_tracking_indices']
    
    # 1. 精确匹配
    if tracking_code == primary_code:
        return True, 'same_as_primary'
    
    # 2. 代码匹配
    if tracking_code in acceptable:
        return True, 'accepted_alternative'
    
    # 3. 关键词匹配
    benchmark = etf_row['benchmark']
    for keyword in acceptable:
        if '.' not in keyword and keyword in benchmark:
            return True, 'accepted_alternative'
    
    return False, 'rejected'
```

## 成功案例

### 有色金属主题
- **主题分析指数**: 000819.SH（中证有色金属指数）
- **匹配到22只ETF**，包括：
  - 512400.SH - 有色金属ETF南方（跟踪：中证申万有色金属指数）
  - 159881.SZ - 有色金属ETF国泰（跟踪：中证有色金属指数）
  - 159032.SZ - 工业有色ETF易方达（跟踪：中证工业有色金属主题指数）
- **匹配关系**: accepted_alternative（通过"有色金属"关键词）
- **验证**: 所有ETF都与有色金属主题高度相关 ✓

### 医药主题
- **主题分析指数**: 000933.SH（中证医药指数）
- **匹配到59只ETF**，包括：
  - 512290.SH - 生物医药ETF国泰（在daily_bars中，可计算流动性）
  - 多只港股通医疗ETF
  - 多只科创医药ETF
- **匹配关系**: accepted_alternative（通过"医药"、"医疗"关键词）
- **验证**: 覆盖A股、港股、科创板医药ETF ✓

## 总结

✅ **已完成**:
1. 架构调整：主题分析指数与ETF跟踪指数解耦
2. 匹配逻辑：支持精确匹配、代码匹配、关键词匹配
3. 配置文件：22个主题的完整配置
4. 候选清单：668只ETF的完整候选清单

❌ **待完成**:
1. 采集主题ETF历史数据（约100-150只）
2. 采集主题分析指数数据（14个可用指数）
3. 解决6个缺失指数的数据源问题
4. 优化配置和流动性阈值
5. 验证和测试

🎯 **下一步**: 开始采集主题ETF和指数的历史数据
