.PHONY: help install dev up down clean test lint format

help:
	@echo "Fund Quant System - Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make install    - 安装依赖"
	@echo "  make dev        - 安装开发依赖"
	@echo "  make up         - 启动服务"
	@echo "  make down       - 停止服务"
	@echo "  make clean      - 清理临时文件"
	@echo "  make test       - 运行测试"
	@echo "  make lint       - 代码检查"
	@echo "  make format     - 代码格式化"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

up:
	docker-compose up -d

down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf build dist *.egg-info

test:
	pytest tests/ -v --cov=src/fund_quant

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/ scripts/
	ruff check --fix src/ tests/
