.PHONY: help install dev test lint format typecheck clean docker-build docker-run

help: ## Show this help message
	@echo "Vanta Bot Development Commands"
	@echo "=============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt
	pip install -e .[dev]
	pre-commit install

dev-install: ## Install dev dependencies (venv assumed active)
	pip install -U pip
	pip install -e .[dev]

dev: ## Start development environment
	docker-compose up -d postgres redis
	@echo "Waiting for services to start..."
	sleep 5
	python -m vantabot

test: ## Run tests
	pytest -q

test-unit: ## Run unit tests
	pytest -q tests/unit

test-integration: ## Run integration tests
	pytest -q tests/integration

test-all: ## Run all tests including integration
	pytest -q

lint: ## Run linting
	ruff check .
	ruff format --check .

format: ## Format code
	ruff format .
	ruff check --fix .

typecheck: ## Run type checking
	mypy src/

type-check: ## Alias for type checking
	mypy src/

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build: ## Build Docker image
	docker build -t vantabot:latest .

docker-run: ## Run Docker container
	docker run --rm -it --env-file .env vantabot:latest

docker-prod: ## Build and run production Docker image
	docker build -f Dockerfile.prod -t vantabot:prod .
	docker-compose -f docker-compose.prod.yml up -d

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MESSAGE="description")
	alembic revision --autogenerate -m "$(MESSAGE)"

logs: ## View application logs
	docker-compose logs -f vantabot

shell: ## Open Python shell with app context
	python -c "from src.config.settings import settings; from src.database.session import get_session; print('Vanta Bot shell ready')"

check: lint typecheck test ## Run all checks

ci: ## Run CI pipeline locally
	ruff check .
	mypy src/
	pytest -q tests/unit
	@echo "✅ All CI checks passed"

setup: install migrate ## Complete setup for development
	@echo "✅ Development environment ready"
	@echo "Run 'make dev' to start the bot"

rotate-deks: ## Rotate DEK encryption keys (Phase 1)
	python scripts/rewrap_deks.py

tx-reconcile: ## Reconcile nonce with on-chain state (Phase 2)
	python -c "from web3 import Web3; \
from src.config.settings import settings; \
from src.database.session import SessionLocal; \
from src.blockchain.tx.orchestrator import TxOrchestrator; \
w3 = Web3(Web3.HTTPProvider(str(settings.BASE_RPC_URL))); \
db = SessionLocal(); \
orch = TxOrchestrator(w3, db); \
print(f'Reconciled nonce: {orch.reconcile_nonce()}'); \
db.close()"

validate-markets: ## Validate market configuration (Phase 3)
	@echo "🔍 Validating markets..."
	@python -c "from web3 import Web3; from src.config.settings import settings; from src.startup.markets_validator import validate_markets_and_feeds; w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL)); validate_markets_and_feeds(w3); print('✅ Markets validated')"

indexer: ## Run Avantis indexer (Phase 4)
	python -m src.services.indexers.avantis_indexer

backfill: ## Run one-shot indexer backfill (Phase 4)
	@python -c "from web3 import Web3; from sqlalchemy import create_engine; from sqlalchemy.orm import sessionmaker; \
from src.config.settings import settings; from src.services.indexers.avantis_indexer import run_once; \
w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL)); \
Session = sessionmaker(bind=create_engine(settings.DATABASE_URL.replace('sqlite+aiosqlite:', 'sqlite:'))); \
print(f'Processed {run_once(w3, Session)} blocks')"

run-bot: ## Run Telegram bot (Phase 5)
	python -m src.bot.application

bot-lint: ## Lint bot code (Phase 5)
	ruff check src/bot

bot-test: ## Test bot code (Phase 5)
	pytest -q tests/bot tests/unit/repositories/test_user_wallets_repo.py

run-webhook: ## Run webhook API (Phase 6)
	python -m src.api

run-worker: ## Run signal worker (Phase 6)
	python -m src.workers.signal_worker

queue-peek: ## Peek at signal queue (Phase 6)
	@python -c "import redis; from src.config.settings import settings; r=redis.from_url(settings.REDIS_URL); items=r.lrange(settings.SIGNALS_QUEUE,0,20); print(f'Queue length: {len(items)}'); [print(i.decode()) for i in items]"

run-tpsl: ## Run TP/SL executor (Phase 7)
	python -m src.services.executors.tpsl_executor

metrics-curl: ## Curl metrics endpoint (Phase 8)
	curl -s http://127.0.0.1:8090/metrics | head -n 30

logs-json: ## Show JSON logs (Phase 8)
	@echo "Set COMPONENT env var per process (webhook, worker, tpsl, bot)"

docker-build: ## Build all Docker images (Phase 9)
	@TAG=$$(git rev-parse --short HEAD) && \
	for svc in bot webhook worker tpsl indexer; do \
		echo "Building $$svc..." && \
		docker build -f docker/Dockerfile.$$svc -t vanta/$$svc:$$TAG -t vanta/$$svc:latest .; \
	done

docker-up: ## Start all services with docker-compose (Phase 9)
	docker compose -f docker/compose.yml up -d

docker-down: ## Stop all services (Phase 9)
	docker compose -f docker/compose.yml down

docker-logs: ## Tail docker logs (Phase 9)
	docker compose -f docker/compose.yml logs -f --tail=100

prod-migrate: ## Run migrations (Phase 9)
	python ops/migrate.py

prod-backup: ## Backup database (Phase 9)
	bash ops/backup.sh
