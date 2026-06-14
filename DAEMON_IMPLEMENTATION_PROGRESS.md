# 财联社新闻 Daemon 实施进度

## 已完成 ✅

### 1. Pipeline 模型层
- ✅ `src/fund_quant/pipelines/news_pipeline/pipeline_models.py`
  - NewsProcessResult - 单条新闻处理结果
  - BatchProcessResult - 批次处理结果
  - DaemonRunResult - Daemon单轮运行结果

### 2. 单条新闻处理流水线
- ✅ `src/fund_quant/pipelines/news_pipeline/single_news_pipeline.py`
  - SingleNewsPipeline类
  - 规则过滤 → Unknown二次过滤 → AI抽取
  - 异常捕获，不中断流程

### 3. 错误分类器
- ✅ `src/fund_quant/research/news_review/error_classifier.py`
  - ErrorClassifier类
  - 12条自动错误标签规则
  - 用于样本筛选和人工复盘

---

## 待实现 📋

### 4. 批次处理流水线
**文件**: `src/fund_quant/pipelines/news_pipeline/cls_batch_pipeline.py`

**功能**:
- ClsBatchPipeline类
- 调用ClsApiCollector抓取
- 去重判断（ClickHouse或本地文件）
- 批量调用SingleNewsPipeline
- 汇总BatchProcessResult
- 保存JSONL/CSV/summary

**关键方法**:
```python
def __init__(self, config)
def run_once(self) -> BatchProcessResult
def _fetch_news(self) -> DataFrame
def _check_duplicates(self, news_list) -> (new_list, dup_list)
def _save_raw_news(self, news_list)
def _save_extracted_events(self, results)
def _save_outputs(self, batch_result)
```

### 5. 报告生成器
**文件**: `src/fund_quant/pipelines/news_pipeline/pipeline_reporter.py`

**功能**:
- print_news_result(result, verbose)
- print_batch_summary(batch_result)
- print_daemon_loop_summary(daemon_run)
- save_jsonl(batch_result, path)
- save_csv(batch_result, path)
- save_summary_md(batch_result, path)

### 6. 去重管理器
**文件**: `src/fund_quant/data/storage/news_dedup_manager.py`

**功能**:
- NewsDedupManager类
- ClickHouse查询news_id是否存在
- 本地文件seen_news_ids.txt作为fallback
- 写入raw_news表

### 7. 事件存储器
**文件**: `src/fund_quant/data/storage/event_repository.py`

**功能**:
- EventRepository类
- 写入extracted_events表
- 兼容处理复杂字段（Array转JSON）

### 8. Daemon主程序
**文件**: `scripts/news_lab/run_cls_daemon.py`

**功能**:
- 参数解析
- 无限循环轮询
- 优雅退出（Ctrl+C）
- 错误重试
- 累计统计

### 9. 人工复盘导出
**文件**: `scripts/news_lab/export_review_csv.py`

**功能**:
- 合并多个batch的JSONL
- 导出人工标注CSV
- 包含系统字段+人工标注字段

### 10. 测试
**文件**: `tests/pipelines/test_cls_daemon.py`

**测试场景**:
- max_loops=1正常退出
- 重复新闻只处理新增
- ClickHouse不可用时fallback本地文件
- 单条失败不中断
- KeyboardInterrupt优雅退出
- 文件正常生成

---

## 目录结构

```
src/fund_quant/
├── pipelines/
│   └── news_pipeline/
│       ├── __init__.py
│       ├── pipeline_models.py          ✅
│       ├── single_news_pipeline.py     ✅
│       ├── cls_batch_pipeline.py       📋
│       └── pipeline_reporter.py        📋
│
├── data/
│   └── storage/
│       ├── news_dedup_manager.py       📋
│       └── event_repository.py         📋
│
└── research/
    └── news_review/
        ├── __init__.py
        └── error_classifier.py         ✅

scripts/
└── news_lab/
    ├── run_cls_daemon.py               📋
    └── export_review_csv.py            📋

data/
└── review/
    ├── cls_batch_outputs/              (自动创建)
    │   ├── cls_20260613_220000_loop0001.jsonl
    │   ├── cls_20260613_220000_loop0001.csv
    │   └── cls_20260613_220000_loop0001_summary.md
    ├── seen_cls_news_ids.txt           (自动创建)
    └── human_labels/                   (人工标注)

logs/
└── cls_daemon.log                      (自动创建)
```

---

## 下一步执行

由于响应长度限制，请告诉我：

**选项A**: 继续实现剩余模块（我会分批完成）
**选项B**: 先测试已完成的3个模块是否符合预期
**选项C**: 我提供详细实现思路和伪代码，你自己完成剩余模块

建议选择**A**，我分批把剩余7个模块实现完整。

---

## 已知依赖

需要的Python包（已安装）:
- pandas
- pyyaml
- python-dotenv
- clickhouse-driver (如果需要)

需要的目录（脚本会自动创建）:
- data/review/cls_batch_outputs/
- data/review/human_labels/
- logs/

需要的数据库表（可选）:
- raw_news
- extracted_events

如果ClickHouse未就绪，系统会fallback到本地文件去重。
