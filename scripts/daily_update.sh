#!/bin/bash
# 每日数据更新脚本

set -e

echo "========================================"
echo "开始每日数据更新"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

cd "$(dirname "$0")/.."

# 1. 更新所有日线数据（主题指数 + 宽基指数 + 主题ETF）
echo ""
echo "[1/2] 更新日线数据（增量模式）..."
uv run python scripts/collect_daily_bars.py --type all --incremental

# 2. 计算主题因子
echo ""
echo "[2/2] 计算主题因子..."
uv run python scripts/calculate_theme_factors.py --days 10

# 3. 显示最新排名
echo ""
echo "========================================"
echo "最新主题强度排名"
echo "========================================"
uv run python scripts/query_theme_strength.py --mode composite --limit 10

echo ""
echo "========================================"
echo "每日更新完成"
echo "========================================"
