.PHONY: help install fmt lint typecheck sec test all clean pre-commit setup-dev

# Default target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -e ".[dev]"

# Code formatting
fmt: ## Format code with black and isort
	black .
	isort .

# Linting
lint: ## Run ruff linter
	ruff check .

lint-fix: ## Run ruff linter with auto-fix
	ruff check --fix .

# Type checking
typecheck: ## Run mypy type checker
	mypy src

# Security checks
sec: ## Run security checks (bandit, safety)
	bandit -q -r src || true
	safety check -r requirements.txt || true

# Testing
test: ## Run tests
	pytest -q

test-verbose: ## Run tests with verbose output
	pytest -v

test-coverage: ## Run tests with coverage
	pytest --cov=src --cov-report=html --cov-report=term

# Pre-commit
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

# Development setup
setup-dev: install-dev pre-commit-install ## Setup development environment
	@echo "Development environment setup complete!"

# Quality checks
quality: fmt lint typecheck ## Run all quality checks

# Full pipeline
all: fmt lint typecheck sec test ## Run all checks and tests

# Database operations
db-upgrade: ## Run database migrations
	alembic upgrade head

db-downgrade: ## Rollback database migrations
	alembic downgrade -1

db-revision: ## Create new database migration
	alembic revision --autogenerate -m "$(MSG)"

db-current: ## Show current database revision
	alembic current

db-history: ## Show database migration history
	alembic history

# Docker operations
docker-build: ## Build Docker image
	docker build -t avantis-telegram-bot .

docker-run: ## Run Docker container
	docker run --rm -it --env-file .env avantis-telegram-bot

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

# Bot operations
bot-start: ## Start the bot
	python main.py

bot-check: ## Check bot configuration
	python scripts/check_avantis_sdk.py

bot-sanity: ## Run sanity checks
	python scripts/sanity_checks.py

# Indexer operations
indexer-start: ## Start the indexer
	python -m src.services.indexers.run_indexer

indexer-check: ## Check indexer status
	python -m src.services.indexers.abi_inspector

# Database optimization
db-optimize: ## Optimize database performance
	python scripts/database_optimize.py

# Cleanup
clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

# Documentation
docs-serve: ## Serve documentation locally
	@echo "Documentation available at:"
	@echo "- README.md - Main documentation"
	@echo "- GO_LIVE_RUNBOOK.md - Deployment guide"
	@echo "- TROUBLESHOOTING.md - Problem solving"
	@echo "- AVANTIS_SDK_INTEGRATION.md - SDK integration"

# Monitoring
logs: ## View application logs
	tail -f logs/app.log

logs-error: ## View error logs only
	grep -i error logs/app.log | tail -20

# Health checks
health: ## Run health checks
	python scripts/sanity_checks.py
	@echo "✅ Health checks completed"

# Production deployment
deploy-check: ## Check deployment readiness
	@echo "Checking deployment readiness..."
	@python scripts/sanity_checks.py
	@echo "✅ Deployment checks passed"

deploy: ## Deploy to production (requires proper configuration)
	@echo "Deploying to production..."
	@echo "⚠️  Make sure to configure production environment first"
	@echo "Use: make deploy-check to verify readiness"

# Environment setup
env-example: ## Copy example environment file
	cp env.example .env
	@echo "✅ Copied env.example to .env"
	@echo "⚠️  Please edit .env with your actual values"

env-production: ## Copy production environment template
	cp env.production.template .env
	@echo "✅ Copied env.production.template to .env"
	@echo "⚠️  Please edit .env with your production values"

# Git operations
git-hooks: ## Install git hooks
	@echo "Installing git hooks..."
	@echo "#!/bin/sh" > .git/hooks/pre-commit
	@echo "make pre-commit" >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ Git hooks installed"

# Performance
perf-test: ## Run performance tests
	pytest tests/ -k "performance" -v

perf-profile: ## Profile application performance
	python -m cProfile -o profile.stats main.py
	@echo "Profile saved to profile.stats"

# Backup and restore
backup-db: ## Backup database
	@echo "Backing up database..."
	@cp vanta_bot.db vanta_bot.db.backup.$(shell date +%Y%m%d_%H%M%S)
	@echo "✅ Database backed up"

restore-db: ## Restore database from backup
	@echo "Available backups:"
	@ls -la vanta_bot.db.backup.* 2>/dev/null || echo "No backups found"
	@echo "Usage: make restore-db BACKUP=filename"

# Version management
version: ## Show current version
	@python -c "import src; print(f'Version: {src.__version__}')"

version-bump: ## Bump version (requires VERSION variable)
	@echo "Bumping version to $(VERSION)"
	@sed -i '' 's/version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@echo "✅ Version bumped to $(VERSION)"

# Development workflow
dev-start: ## Start development environment
	@echo "Starting development environment..."
	@make env-example
	@make setup-dev
	@echo "✅ Development environment ready!"
	@echo "Next steps:"
	@echo "1. Edit .env with your configuration"
	@echo "2. Run 'make bot-start' to start the bot"
	@echo "3. Run 'make test' to run tests"

# CI/CD helpers
ci-install: ## Install dependencies for CI
	pip install -r requirements.txt
	pip install -e ".[dev]"

ci-test: ## Run tests for CI
	pytest --cov=src --cov-report=xml --cov-report=term

ci-lint: ## Run linting for CI
	ruff check --output-format=github .

ci-typecheck: ## Run type checking for CI
	mypy src --show-error-codes

ci-sec: ## Run security checks for CI
	bandit -r src -f json -o bandit-report.json
	safety check -r requirements.txt --json --output safety-report.json

ci-all: ci-install ci-lint ci-typecheck ci-sec ci-test ## Run all CI checks
