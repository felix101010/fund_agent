# 多源新闻 Pipeline 架构升级 - 实施总结

**日期**: 2026-06-17  
**状态**: ✅ 完成

## 一、升级目标

将原来强绑定财联社的批处理 Pipeline 升级为通用多源架构，支持：
- cls（财联社）
- wallstreetcn（华尔街见闻）
- jin10（金十数据）
- reuters（路透社）
- x（Twitter）
- xueqiu（雪球）
- 以及未来任意新闻源

## 二、核心设计原则

1. ✅ **最小改动** - 不重构整个项目
2. ✅ **复用现有** - SingleNewsPipeline、PipelineReporter 继续使用
3. ✅ **向后兼容** - 保留 ClsBatchPipeline，不破坏现有脚本
4. ✅ **通用设计** - 新增 NewsBatchPipeline，一个 Pipeline 支持所有源
5. ✅ **分源存储** - 按来源保存 + 全局汇总

## 三、修改的文件

### 1. pipeline_models.py（修改）

**修改内容**:
- 在 `NewsProcessResult` 中添加 `source_role` 字段
- 类型：`str = ""`
- 用途：区分新闻源角色
  - `a_share_catalyst` - A股催化剂（财联社）
  - `market_context` - 市场上下文（华尔街见闻）
  - `macro_event` - 宏观事件（金十）
  - `global_primary` - 全球一手（路透社）

### 2. pipeline_reporter.py（扩展）

**新增方法**:
- `append_results_to_jsonl(results: list, jsonl_path: str)`
  - 支持保存结果列表到任意 JSONL 文件
  - 支持 `source_role` 字段
  - 支持 `url` 字段
  - `ensure_ascii=False`，支持中文

- `save_batch_summary(batch_result, md_path: str)`
  - 包装方法，方便调用

**保留**:
- 原有 `append_jsonl()` 方法不变
- 原有打印和汇总方法不变

### 3. cls_batch_pipeline.py（注释说明）

**修改内容**:
- 顶部添加说明注释：
  ```python
  """
  财联社批次处理流水线（历史专用版本）
  
  注意：
  - 这是历史遗留的财联社专用 pipeline
  - 新新闻源建议使用 NewsBatchPipeline（news_batch_pipeline.py）
  - 本文件暂时保留以兼容现有脚本
  """
  ```

**保留**:
- 所有原有逻辑不变
- 现有脚本（run_cls_daemon.py）继续可用

## 四、新增的文件

### 1. news_batch_pipeline.py（核心）

**位置**: `src/fund_quant/pipelines/news_pipeline/news_batch_pipeline.py`

**类名**: `NewsBatchPipeline`

**核心功能**:
- 通用多源批处理
- 兼容 DataFrame 和 List[RawNews] 返回格式
- 自动按来源分文件保存
- 同时保存全局汇总文件
- 支持自定义 seen 文件路径

**初始化参数**:
```python
NewsBatchPipeline(
    source: str,                      # 新闻源名称
    collector,                        # 采集器实例
    source_role: str = "",           # 新闻源角色
    limit: int = 20,                 # 抓取数量
    only_new: bool = True,           # 只处理新增
    verbose: bool = False,           # 详细输出
    model: Optional[str] = None,     # AI模型
    save_raw: bool = False,          # 保存原始新闻
    save_events: bool = False,       # 保存结构化事件
    save_jsonl: bool = True,         # 保存JSONL
    save_by_source_jsonl: bool = True,   # 按来源保存
    save_global_jsonl: bool = True,      # 保存全局文件
    save_summary: bool = True,       # 生成摘要
    output_dir: str = "data/review/news_batch_outputs",
    seen_file_path: Optional[str] = None  # seen文件路径
)
```

**核心方法**:
- `run_once(run_id, loop_index) -> BatchProcessResult`
- `_iter_news_rows(data)` - 兼容多种数据格式
- `_process_single_news(item, batch_id, run_id)` - 处理单条
- `_generate_stats(batch_result)` - 生成统计
- `_save_jsonl_outputs(batch_result)` - 保存JSONL
- `_save_summary(batch_result)` - 保存摘要

### 2. test_wallstreetcn_batch_pipeline.py

**位置**: `scripts/test_wallstreetcn_batch_pipeline.py`

**功能**: 测试华尔街见闻批处理

**使用方法**:
```bash
python scripts/test_wallstreetcn_batch_pipeline.py
```

### 3. test_cls_news_batch_pipeline.py（可选）

**位置**: `scripts/test_cls_news_batch_pipeline.py`

**功能**: 验证新 Pipeline 也能处理财联社新闻

**使用方法**:
```bash
python scripts/test_cls_news_batch_pipeline.py
```

## 五、输出文件结构

### 新的输出目录结构

```
data/review/news_batch_outputs/
├── processed_news_all.jsonl           # 全局汇总（所有源）
├── by_source/                         # 按来源分文件
│   ├── cls_news_all.jsonl            # 财联社
│   ├── wallstreetcn_news_all.jsonl   # 华尔街见闻
│   ├── jin10_news_all.jsonl          # 金十（未来）
│   └── reuters_news_all.jsonl        # 路透（未来）
└── summaries/                         # 摘要文件
    ├── cls_20260617_143025_loop0001_summary.md
    ├── wallstreetcn_20260617_143100_loop0001_summary.md
    └── ...
```

### seen 文件（去重）

每个源独立的 seen 文件：
```
data/review/
├── seen_cls_news_ids.txt
├── seen_wallstreetcn_news_ids.txt
├── seen_jin10_news_ids.txt
└── seen_reuters_news_ids.txt
```

**为什么分文件**:
- 不同源的 news_id 格式不同，避免冲突
- 例如：`cls_2402754` vs `wscn_3712345`
- 跨源去重以后再做，不在本次范围

## 六、使用方法

### 6.1 华尔街见闻（示例）

```python
from fund_quant.pipelines.news_pipeline.news_batch_pipeline import NewsBatchPipeline
from fund_quant.data_sources.news.wallstreetcn_collector import WallstreetcnCollector

# 初始化
collector = WallstreetcnCollector()
pipeline = NewsBatchPipeline(
    source="wallstreetcn",
    source_role="market_context",
    collector=collector,
    limit=20,
    output_dir="data/review/news_batch_outputs",
)

# 运行
batch_result = pipeline.run_once(run_id="test_001", loop_index=1)
```

### 6.2 财联社（使用新 Pipeline）

```python
from fund_quant.pipelines.news_pipeline.news_batch_pipeline import NewsBatchPipeline
from fund_quant.data_sources.news.cls_api_collector import ClsApiCollector

# 初始化
collector = ClsApiCollector()
pipeline = NewsBatchPipeline(
    source="cls",
    source_role="a_share_catalyst",
    collector=collector,
    limit=20,
)

# 运行
batch_result = pipeline.run_once(run_id="test_002", loop_index=1)
```

### 6.3 未来接入新源（示例：金十）

```python
# 1. 创建采集器
class Jin10Collector:
    SOURCE = "jin10"
    
    def fetch_latest(self, limit=20):
        # 返回 DataFrame 或 List[RawNews]
        pass

# 2. 使用 NewsBatchPipeline
collector = Jin10Collector()
pipeline = NewsBatchPipeline(
    source="jin10",
    source_role="macro_event",
    collector=collector,
    limit=30,
)

batch_result = pipeline.run_once(run_id="jin10_001", loop_index=1)
```

## 七、为什么同时保存两套文件

### 按来源保存（by_source/）

**优点**:
- 便于按源查看和分析
- 方便单独删除某个源的数据
- 支持不同源的独立配置
- 便于监控单个源的质量

**使用场景**:
- 查看华尔街见闻所有新闻：`by_source/wallstreetcn_news_all.jsonl`
- 统计财联社采集量
- 调试单个源的问题

### 全局汇总（processed_news_all.jsonl）

**优点**:
- 一个文件包含所有源
- 便于全局搜索和分析
- 支持跨源去重（未来）
- 便于生成综合报告

**使用场景**:
- 搜索所有新闻中的"英伟达"
- 统计今天所有源的新闻总量
- 跨源主题分析
- 导入数据库

**两者关系**:
- 内容完全一致，只是组织方式不同
- 每条新闻同时写入两个地方
- 可以通过配置单独关闭某一个

## 八、数据兼容性

### Collector 返回格式兼容

NewsBatchPipeline 自动兼容两种返回格式：

**格式1：DataFrame（财联社）**
```python
# ClsApiCollector.fetch_latest() 返回 DataFrame
df = collector.fetch_latest(limit=20)
# Pipeline 通过 iterrows() 遍历
```

**格式2：List[RawNews]（华尔街见闻）**
```python
# WallstreetcnCollector.fetch_latest() 返回 List[RawNews]
news_list = collector.fetch_latest(limit=20)
# Pipeline 直接遍历 list
```

**实现方式**:
```python
def _iter_news_rows(self, data):
    if isinstance(data, pd.DataFrame):
        for _, row in data.iterrows():
            yield row
    elif isinstance(data, list):
        for item in data:
            yield item
```

### 字段提取兼容

使用 `get_field()` 函数兼容多种对象类型：
- dict
- pandas.Series
- dataclass
- 普通 object

## 九、测试验收

### 测试1：华尔街见闻

```bash
python scripts/test_wallstreetcn_batch_pipeline.py
```

**预期输出**:
```
华尔街见闻批处理 Pipeline 测试
================================================================================
1. 初始化华尔街见闻采集器...
   ✓ 采集器初始化完成

2. 初始化批处理 Pipeline...
   ✓ Pipeline 初始化完成

3. 运行一轮批处理...

批次: wallstreetcn_20260617_143025_loop0001
================================================================================
1. 采集 wallstreetcn 新闻...
  抓取到 20 条
2. 去重...
3. 逐条处理...

测试结果汇总
================================================================================
batch_id: wallstreetcn_20260617_143025_loop0001
run_id: test_wallstreetcn_20260617_143025

总抓取数: 20
新增新闻: 18
重复新闻: 2
处理数量: 18

AI成功: 5
AI失败: 0
fallback: 0

输出文件:
  按来源: data/review/news_batch_outputs/by_source/wallstreetcn_news_all.jsonl
  全局文件: data/review/news_batch_outputs/processed_news_all.jsonl
  摘要文件: data/review/news_batch_outputs/summaries/wallstreetcn_20260617_143025_loop0001_summary.md
```

### 测试2：财联社（新Pipeline）

```bash
python scripts/test_cls_news_batch_pipeline.py
```

**预期输出**: 类似华尔街见闻，但 source=cls

### 测试3：原有财联社 Daemon（兼容性）

```bash
python scripts/news_lab/run_cls_daemon.py --max-loops 1 --limit 10
```

**预期**: 正常运行，输出到原位置

## 十、未来扩展

### 10.1 接入新源的步骤

1. **创建 Collector**
   ```python
   class NewSourceCollector:
       SOURCE = "newsource"
       
       def fetch_latest(self, limit=20):
           # 返回 DataFrame 或 List[RawNews]
           pass
   ```

2. **使用 NewsBatchPipeline**
   ```python
   pipeline = NewsBatchPipeline(
       source="newsource",
       source_role="...",
       collector=NewSourceCollector(),
   )
   ```

3. **创建测试脚本**
   ```python
   # scripts/test_newsource_batch_pipeline.py
   ```

4. **运行测试**
   ```bash
   python scripts/test_newsource_batch_pipeline.py
   ```

### 10.2 多源 Daemon（未来）

可以创建 `multi_source_daemon.py`：
```python
sources = [
    ("cls", ClsApiCollector(), "a_share_catalyst"),
    ("wallstreetcn", WallstreetcnCollector(), "market_context"),
    ("jin10", Jin10Collector(), "macro_event"),
]

for source, collector, role in sources:
    pipeline = NewsBatchPipeline(source, collector, role, ...)
    pipeline.run_once(...)
```

### 10.3 跨源去重（未来）

可以在 NewsBatchPipeline 中添加：
```python
def _check_cross_source_duplicate(self, item):
    # 基于 title + publish_time 跨源去重
    pass
```

## 十一、注意事项

### ✅ 做了的事

1. ✅ 创建通用 NewsBatchPipeline
2. ✅ 添加 source_role 字段
3. ✅ 扩展 PipelineReporter
4. ✅ 兼容 DataFrame 和 List 返回格式
5. ✅ 按来源分文件 + 全局汇总
6. ✅ 独立 seen 文件
7. ✅ 保留原有 ClsBatchPipeline
8. ✅ 创建测试脚本

### ❌ 没做的事（按要求）

1. ❌ 没有重构 SingleNewsPipeline
2. ❌ 没有重写 AIEventExtractor
3. ❌ 没有改财联社 Collector
4. ❌ 没有改华尔街见闻 Collector
5. ❌ 没有引入复杂调度框架
6. ❌ 没有删除 cls_batch_pipeline.py
7. ❌ 没有一次性做 MultiSourceDaemon
8. ❌ 没有大改数据库结构

## 十二、文件清单

### 修改的文件（3个）

1. `src/fund_quant/pipelines/news_pipeline/pipeline_models.py`
2. `src/fund_quant/pipelines/news_pipeline/pipeline_reporter.py`
3. `src/fund_quant/pipelines/news_pipeline/cls_batch_pipeline.py`

### 新增的文件（3个）

4. `src/fund_quant/pipelines/news_pipeline/news_batch_pipeline.py`
5. `scripts/test_wallstreetcn_batch_pipeline.py`
6. `scripts/test_cls_news_batch_pipeline.py`

完成！🚀
