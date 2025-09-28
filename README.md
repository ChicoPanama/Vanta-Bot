# 🚀 Vanta Bot — Telegram Trading on Base (Avantis)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](docker-compose.yml)
[![Base Network](https://img.shields.io/badge/Network-Base%20L2-8B5CF6.svg)](https://base.org)

Production‑ready Telegram bot for the Avantis Protocol on Base. Includes copy‑trading, price oracles (Pyth + Chainlink), background indexers, optional Avantis Trader SDK integration, and health/metrics endpoints.

Key entry points:
- Bot entry: `main.py:1`
- Bot app factory: `src/bot/application.py:1`
- Health server (FastAPI): `src/monitoring/health_server.py:1`
- Settings & flags: `src/config/settings.py:1`, `src/config/flags.py:1`

## Features

- Telegram bot with modular handlers (start, wallet, trade, positions, portfolio, orders, settings)
- Copy‑trading UX and commands (`/alfa`, `/follow`, `/status`, `/unfollow`)
- AI/analytics surfaces (leaderboard, insights, position tracking)
- Oracle facade with Pyth + Chainlink providers and deviation/freshness checks
- Background services: Avantis indexer, price feed client, health monitoring
- Envelope encryption support (AWS KMS or local Fernet) for wallets
- Async SQLAlchemy models and operations (SQLite/Postgres)
- Redis‑backed execution mode and rate limiting utilities
- Health and metrics endpoints (FastAPI) for ops

See project structure: `docs/project-structure.md`

## Quick Start

Development (local, minimal requirements):
```bash
git clone <repo>
cd avantis-telegram-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env

# Minimal local overrides
echo "BASE_RPC_URL=memory" >> .env                 # in‑memory Web3
echo "REQUIRE_CRITICAL_SECRETS=false" >> .env      # bypass strict startup checks
echo "ENCRYPTION_KEY=$(python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
)" >> .env

# Set your Telegram bot token
sed -i.bak 's|TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=123456789:ABC...|' .env

python main.py
```

Production‑grade run (real RPC, Redis, DB, secrets set):
```bash
pip install -r requirements.txt
alembic upgrade head
ENVIRONMENT=production LOG_JSON=true python main.py
```

Docker:
```bash
docker-compose up -d
```

Enterprise deploy script: `python scripts/deploy_enterprise.py`

## Step‑by‑Step Setup (No Gaps)

1) Install prerequisites
- macOS (Homebrew): `brew install python@3.11 redis`
- Ubuntu/Debian: `sudo apt update && sudo apt install -y python3.11 python3.11-venv redis-server`
- Windows: Install Python 3.11, use PowerShell, consider WSL for best parity

2) Create and activate venv
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3) Install deps
```bash
pip install -r requirements.txt
```

4) Configure environment
```bash
cp env.example .env
# Edit .env with your values (TELEGRAM_BOT_TOKEN at minimum)
# For local dev add:
echo "BASE_RPC_URL=memory" >> .env
echo "REQUIRE_CRITICAL_SECRETS=false" >> .env
python scripts/generate_key.py  # copy the key into ENCRYPTION_KEY in .env
```

5) Initialize database (optional; SQLite auto‑creates; Postgres requires migrations)
```bash
# SQLite (default): nothing to do
# PostgreSQL example:
export DATABASE_URL=postgresql://user:pass@localhost:5432/vanta_bot
alembic upgrade head
```

6) Run the bot
```bash
python main.py
```

7) Start health API (optional but recommended)
```bash
uvicorn src.monitoring.health_server:app --host 0.0.0.0 --port ${HEALTH_PORT:-8080}
curl -s http://localhost:8080/health | jq .
```

8) Talk to your bot
- In Telegram, message your bot (BotFather token) and send `/start`
- Follow the menus or use commands listed below

## Configuration

Required for development quick start:
- `TELEGRAM_BOT_TOKEN` – token from BotFather
- `ENCRYPTION_KEY` – Fernet key (see generation above)
- `DATABASE_URL` – defaults to `sqlite+aiosqlite:///vanta_bot.db`
- `BASE_RPC_URL` – set to `memory` for local dev or a real Base RPC URL

Required for live trading (choose a signer backend):
- Local signer: `TRADER_PRIVATE_KEY` (hex) and `SIGNER_BACKEND=local`
- AWS KMS signer: `AWS_KMS_KEY_ID`, `AWS_REGION` and `SIGNER_BACKEND=kms`

Core settings (defaults in code):
- Network: `BASE_RPC_URL`, `BASE_CHAIN_ID`, `BASE_WS_URL`
- Data stores: `DATABASE_URL`, `REDIS_URL`
- Security: `KEY_ENVELOPE_ENABLED`, `LOCAL_WRAP_KEY_B64` or `AWS_KMS_KEY_ID`
- Contracts: `AVANTIS_TRADING_CONTRACT`, `AVANTIS_VAULT_CONTRACT`, `USDC_CONTRACT`
- Mode/limits: `COPY_EXECUTION_MODE` (DRY|LIVE), `DEFAULT_SLIPPAGE_PCT`, `MAX_LEVERAGE`, `MAX_COPY_LEVERAGE`
- Admin & ops: `ADMIN_USER_IDS`, `SUPER_ADMIN_IDS`, `HEALTH_PORT`, `ENABLE_METRICS`
- Oracle thresholds: `ORACLE_MAX_DEVIATION_BPS`, `ORACLE_MAX_AGE_S`

Centralized feed config is supported: `config/feeds.json` (see `src/config/feeds_config.py:1`).

Live trading checklist (required)
- Set `SIGNER_BACKEND=local` and `TRADER_PRIVATE_KEY=<hex>` or `SIGNER_BACKEND=kms` with `AWS_KMS_KEY_ID` and `AWS_REGION`
- Set realistic `BASE_RPC_URL` (Alchemy/QuickNode Base) and `BASE_CHAIN_ID=8453`
- Ensure `REDIS_URL` and `DATABASE_URL` point to production services
- Set `COPY_EXECUTION_MODE=LIVE` and verify `/copy mode LIVE` as admin
- Configure contracts: `AVANTIS_TRADING_CONTRACT` (vault auto‑resolved at runtime)
- Keep `LOG_JSON=true` and proper log level in production

## Usage (Telegram Commands)

- Getting started: `/start`, `/help`
- Core: `/wallet`, `/trade`, `/positions`, `/portfolio`, `/orders`, `/settings`
- Risk & education: `/analyze <ASSET> <SIZE> <LEV>`, `/calc <ASSET> <LEV> [risk%]`
- AI & insights: `/alpha`, `/alfa top50`
- Copy trading: `/follow <address>`, `/status`, `/unfollow <address>`
- Admin: `/health`, `/diag`, `/recent_errors`, `/latency`, `/autocopy_off_all`

Handlers are wired via `src/bot/handlers/registry.py:1` and `src/bot/application.py:1`.

### Command Reference with Examples

- `/start`
  - Registers you in the bot and shows the main menu. Required before other commands.
- `/help`
  - Displays a short guide and command list.
- `/markets`
  - Opens market browser with inline buttons for assets and categories.
- `/wallet`
  - Shows your wallet address and balances (ETH, USDC). Deposit USDC to trade.
- `/linkwallet`
  - Starts a short flow to link an external wallet (if supported by your setup).
- `/prefs`
  - Opens your preferences (e.g., default slippage). Stored server‑side.
- `/mode`
  - Switch between simple and advanced UI modes.
- `/trade`
  - Opens the interactive trading UI: choose direction → asset → leverage → type size → confirm.
- `/a_quote <PAIR> <SIDE> <COLL_USDC> <LEV> [slip%]`
  - Power users: get a quote directly.
  - Example: `/a_quote ETH/USD LONG 100 25 1`
  - Shows notional, fees, protection, and allowance status.
- `/positions`
  - Lists your open and recent positions.
- `/portfolio`
  - High‑level portfolio analytics (PnL, win rate, etc.).
- `/orders`
  - Lists pending orders (if applicable).

Copy‑Trading
- `/alfa top50`
  - Shows AI‑ranked trader leaderboard (address, score, volume, risk level) with quick actions.
- `/follow <trader_id_or_address>`
  - Starts follow and opens an inline settings panel (auto‑copy, sizing mode, caps, leverage, slippage, protection). Example: `/follow 0x1234...`
- `/following`
  - Lists your current follows with quick settings/unfollow buttons.
- `/status`
  - Copy‑trading status: leaders followed, open copied positions, 30D P&L/volume/win‑rate.
- `/unfollow <trader_id_or_address>`
  - Stops following a trader.

Admin (only IDs in `ADMIN_USER_IDS`)
- `/copy mode DRY|LIVE`
  - Toggle execution mode. Example: `/copy mode LIVE`
- `/emergency stop|start`
  - Global emergency stop for copy execution.
- `/status`
  - System status summary (admin version). Note: non‑admin users have a different `/status` for copy stats.
- `/health`, `/diag`, `/recent_errors`, `/latency`, `/autocopy_off_all`, `/autocopy_on_user <id>`, `/autocopy_off_user <id>`

Tips
- If you see “User not found. Please /start first.” → run `/start` once.
- If quotes show “Approve USDC”, follow the inline button to set allowance before executing.

## Health & Metrics

- FastAPI app: `src/monitoring/health_server.py:1`
- Endpoints: `/live`, `/ready`, `/health`, `/metrics`

Run separately via uvicorn (recommended):
```bash
uvicorn src.monitoring.health_server:app --host 0.0.0.0 --port ${HEALTH_PORT:-8080}
```

Note: Background health monitoring is started from `src/services/background.py:1`. If endpoints are not available in your run mode, prefer the uvicorn command above.

## Architecture

High‑level overview:
```
Telegram Bot (PTB v20)
  ├─ Handlers: start, wallet, trade, positions, copy_trading
  ├─ Middleware: auth, rate limit, errors
  └─ Services: trading, analytics, copytrading

Background Services
  ├─ Avantis indexer (HTTP+WS)
  ├─ Price feed client (Pyth via Avantis SDK)
  └─ Health monitoring tasks

Core Modules
  ├─ Oracle facade (Pyth + Chainlink)
  ├─ Web3 base client, signers (local/KMS)
  ├─ SQLAlchemy models/ops (SQLite/Postgres)
  └─ Key vault (envelope or legacy Fernet)
```

Key files to explore:
- Bot app: `src/bot/application.py:1`
- Handlers: `src/bot/handlers/*`
- Trading services: `src/services/trading/`
- Copy‑trading: `src/services/copytrading/`
- Oracles: `src/services/oracle.py:1`, `src/services/oracle_providers/`
- Blockchain client: `src/blockchain/base_client.py:1`, `src/blockchain/signers/`
- Background: `src/services/background.py:1`
- Health: `src/monitoring/health_server.py:1`, `src/monitoring/health.py:1`

## Testing

Install dev deps and run tests:
```bash
pip install -r requirements.txt
pytest -q
```

Helpful subsets:
```bash
pytest tests/test_symbols.py -q                   # market symbol normalization
pytest tests/test_oracle_facade_fixed.py -q      # oracle facade behavior
pytest tests/test_execution_mode_redis.py -q     # Redis‑backed execution mode
```

See `docs/TESTING.md` for details.

## Troubleshooting

- Startup validation failed (missing secrets)
  - Set `REQUIRE_CRITICAL_SECRETS=false` for local dev, or provide `TRADER_PRIVATE_KEY`/KMS vars
- Cannot connect to RPC
  - Verify `BASE_RPC_URL` or use `BASE_RPC_URL=memory` for local dev
- Health endpoints not found
  - Run uvicorn: `uvicorn src.monitoring.health_server:app --port 8080`
- Redis warnings during startup
  - Redis is optional; some features degrade gracefully without it

More: `docs/troubleshooting.md`

## Documentation

- Installation: `docs/installation.md`
- Configuration: `docs/configuration.md`
- Architecture: `docs/architecture.md`
- Project structure: `docs/project-structure.md`
- Production hardening: `docs/production-hardening-checklist.md`
- Testing: `docs/TESTING.md`

## Contributing

Pull requests are welcome. Please:
- Add/adjust tests for behavior changes
- Follow existing code style (see linters in `pyproject.toml`)
- Keep docs and `env.example` in sync

See `docs/contributing.md` for guidance.

## License

MIT — see `LICENSE`.

## Acknowledgments

- Avantis Protocol and Base Network
- Open‑source libraries listed in `pyproject.toml`

— Built for decentralized trading on Base
