# Fund Quant System

机构级量化交易系统 - 基于新闻事件驱动的主题/ETF轮动策略

## 系统架构

```
新闻采集 → NLP处理 → 事件抽取 → 主题映射 → 因子计算 → 信号生成 → 组合构建 → 风控 → 执行
```

## 核心能力

- **多源数据采集**: 财联社、巨潮、Reuters、Reddit、X
- **智能NLP**: 事件抽取、情绪分析、实体链接
- **知识图谱**: 主题-行业-个股-ETF映射关系
- **因子研究**: 新闻Alpha、动量、流动性、情绪因子
- **策略引擎**: 主题轮动、ETF轮动、事件驱动
- **风控系统**: 仓位管理、止损、回撤控制
- **回测框架**: 高保真回测、Walk-Forward验证

## 快速开始

```bash
# 安装依赖
make install

# 配置环境
cp .env.example .env
# 编辑 .env 填入API密钥

# 启动服务
make up

# 采集新闻
python scripts/collect_news.py --source all

# 运行回测
python scripts/run_backtest.py --strategy theme_rotation --start 20240101 --end 20241231
```

## 技术栈

- **数据存储**: ClickHouse (时序数据) + Redis (缓存) + Parquet (特征)
- **计算框架**: Pandas + Polars + NumPy
- **NLP**: Transformers + LLM API
- **回测**: 自研高性能回测引擎
- **监控**: Prometheus + Grafana
- **部署**: Docker + Docker Compose

## 目录说明

详见各子目录的 README.md

## License

Proprietary - Internal Use Only
