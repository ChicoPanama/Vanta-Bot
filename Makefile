# Avantis Trading Bot - Development Makefile

.PHONY: help install dev-install test test-unit test-integration test-e2e lint format type-check pre-commit clean build docs

# Default target
help:
	@echo "Avantis Trading Bot - Available Commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          Install production dependencies"
	@echo "  dev-install      Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only (fast)"
	@echo "  test-integration Run integration tests (requires RPC)"
	@echo "  test-e2e         Run end-to-end tests (requires CONFIRM_SEND=YES)"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run type checking with mypy"
	@echo "  pre-commit       Run all pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  clean            Clean up build artifacts"
	@echo "  build            Build package"
	@echo "  docs             Generate documentation"
	@echo ""
	@echo "CLI Tools:"
	@echo "  preflight        Run preflight validation"
	@echo "  monitor          Monitor contract unpause events"
	@echo ""
	@echo "Examples:"
	@echo "  make dev-install && make test-unit"
	@echo "  make pre-commit"
	@echo "  make preflight"

# Installation
install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit -v

test-integration:
	pytest -m integration -v

test-e2e:
	@if [ "$(CONFIRM_SEND)" != "YES" ]; then \
		echo "E2E tests require CONFIRM_SEND=YES"; \
		echo "Run: CONFIRM_SEND=YES make test-e2e"; \
		exit 1; \
	fi
	pytest -m e2e -v

test-coverage:
	pytest tests/unit --cov=src --cov-report=html --cov-report=term

# Code Quality
lint:
	ruff check . --fix
	black --check .
	isort --check-only .

format:
	black .
	isort .

type-check:
	mypy src

pre-commit:
	pre-commit run --all-files

# Development
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build:
	python -m build

docs:
	@echo "Documentation generation not yet implemented"

# CLI Tools
preflight:
	python -m src.cli.preflight

monitor:
	python -m src.cli.monitor_unpaused

# Development helpers
setup-dev: dev-install
	@echo "Setting up development environment..."
	@if [ ! -f env/.env ]; then \
		echo "Copying environment template..."; \
		cp env/.env.example env/.env; \
		echo "Please edit env/.env with your configuration"; \
	fi
	@echo "Development environment ready!"

check-env:
	@echo "Checking environment configuration..."
	@if [ ! -f env/.env ]; then \
		echo "❌ env/.env not found. Run 'make setup-dev' first"; \
		exit 1; \
	fi
	@echo "✅ Environment file found"

# Quick development workflow
quick-test: check-env
	@echo "Running quick development tests..."
	make test-unit
	make lint

# Production readiness check
production-check:
	@echo "Running production readiness checks..."
	make test-unit
	make lint
	make type-check
	@echo "✅ Production readiness check passed"

# Security checks
security-check:
	@echo "Running security checks..."
	@if command -v safety >/dev/null 2>&1; then \
		safety check; \
	else \
		echo "⚠️  safety not installed. Install with: pip install safety"; \
	fi
	@if command -v bandit >/dev/null 2>&1; then \
		bandit -r src; \
	else \
		echo "⚠️  bandit not installed. Install with: pip install bandit"; \
	fi

# Docker helpers (if needed)
docker-build:
	docker build -t avantis-trading-bot .

docker-run:
	docker run --env-file env/.env avantis-trading-bot

# Git helpers
git-setup:
	@echo "Setting up git hooks..."
	pre-commit install
	@echo "✅ Git hooks installed"

# Release helpers
release-check:
	@echo "Running release checks..."
	make production-check
	make security-check
	@echo "✅ Release checks passed"

# Help for specific commands
help-test:
	@echo "Testing Commands:"
	@echo "  make test-unit        - Fast unit tests (no external dependencies)"
	@echo "  make test-integration - Tests requiring RPC access"
	@echo "  make test-e2e         - Full end-to-end tests (requires CONFIRM_SEND=YES)"
	@echo ""
	@echo "Test Examples:"
	@echo "  make test-unit"
	@echo "  BASE_RPC_URL=https://mainnet.base.org make test-integration"
	@echo "  CONFIRM_SEND=YES make test-e2e"

help-cli:
	@echo "CLI Commands:"
	@echo "  make preflight        - Run preflight validation"
	@echo "  make monitor          - Monitor contract unpause events"
	@echo ""
	@echo "CLI Examples:"
	@echo "  make preflight"
	@echo "  python -m src.cli.open_trade --collat 10 --lev 2 --slip 1 --pair 0 --long"
	@echo "  python -m src.cli.preflight --collat 100 --lev 5 --slip 0.5 --pair 1 --short"