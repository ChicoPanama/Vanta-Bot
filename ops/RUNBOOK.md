# Vanta-Bot Operations Runbook

## Daily Checks
- Check CI green on main
- Review logs for errors: `make logs-tail`
- Check metrics: `make metrics-curl`

## Common Incidents

### Redis Down
- Symptom: Queue operations fail
- Fix: `docker compose restart redis`
- Bot retries automatically

### RPC Errors  
- Symptom: Transaction failures
- Fix: Verify BASE_RPC_URL, check provider status
- Bot has backoff and retry logic

### Migration Failures
- Symptom: alembic upgrade fails
- Fix: Review migration, rollback if needed
- Command: `alembic downgrade -1`

### Worker Silent
- Symptom: loop_heartbeat = 0
- Fix: Restart worker service
- Check: Redis connectivity

## Deployment
1. Tag release: `git tag v9.0.0`
2. Push: `git push origin v9.0.0`  
3. Trigger: GitHub Actions build workflow
4. Deploy: Use workflow_dispatch with tag

## Rollback
1. Redeploy previous image tag
2. If schema changed: `alembic downgrade -1`
3. Restart services
