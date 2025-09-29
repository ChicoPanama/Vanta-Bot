# Deployment Guide

This guide covers deploying Vanta Bot in various environments, from development to production.

## Prerequisites

- Docker and Docker Compose
- PostgreSQL database
- Redis instance
- Base network RPC access
- Telegram Bot Token
- Avantis Protocol access

## Environment Setup

### 1. Clone and Configure

```bash
git clone https://github.com/ChicoPanama/Vanta-Bot.git
cd Vanta-Bot
cp .env.example .env
```

### 2. Environment Variables

Edit `.env` with your configuration:

```bash
# Required
TELEGRAM_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@localhost:5432/vantabot
REDIS_URL=redis://localhost:6379/0
RPC_URL_BASE=https://mainnet.base.org
PRIVATE_KEY=your_private_key

# Optional
ENVIRONMENT=production
DEBUG=false
DRY_RUN=false
```

## Development Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f vantabot

# Stop services
docker-compose down
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the bot
python -m vantabot
```

## Production Deployment

### 1. Infrastructure Requirements

**Minimum Specifications:**
- 2 CPU cores
- 4GB RAM
- 50GB SSD storage
- Ubuntu 20.04+ or similar

**Recommended Specifications:**
- 4 CPU cores
- 8GB RAM
- 100GB SSD storage
- Dedicated database server

### 2. Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres createdb vantabot
sudo -u postgres createuser vantabot_user

# Set password
sudo -u postgres psql -c "ALTER USER vantabot_user PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vantabot TO vantabot_user;"
```

### 3. Redis Setup

```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Set: requirepass your_redis_password
# Set: maxmemory 1gb
# Set: maxmemory-policy allkeys-lru

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 4. Docker Production Deployment

```bash
# Build production image
docker build -f Dockerfile.prod -t vantabot:prod .

# Run with production compose
docker-compose -f docker-compose.prod.yml up -d
```

### 5. Systemd Service (Alternative)

```bash
# Copy service file
sudo cp config/vanta-bot.service /etc/systemd/system/

# Edit configuration
sudo nano /etc/systemd/system/vanta-bot.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable vanta-bot
sudo systemctl start vanta-bot
```

## Kubernetes Deployment

### 1. Namespace and ConfigMap

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: vantabot

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vantabot-config
  namespace: vantabot
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  HEALTH_PORT: "8080"
```

### 2. Secret Management

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: vantabot-secrets
  namespace: vantabot
type: Opaque
data:
  telegram-token: <base64-encoded-token>
  private-key: <base64-encoded-key>
  database-url: <base64-encoded-url>
  redis-url: <base64-encoded-url>
```

### 3. Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vantabot
  namespace: vantabot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vantabot
  template:
    metadata:
      labels:
        app: vantabot
    spec:
      containers:
      - name: vantabot
        image: vantabot:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: vantabot-config
        - secretRef:
            name: vantabot-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

## Monitoring and Health Checks

### 1. Health Endpoints

- **Health Check**: `GET /health`
- **Readiness**: `GET /ready`
- **Metrics**: `GET /metrics`

### 2. Prometheus Monitoring

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'vantabot'
    static_configs:
      - targets: ['vantabot:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### 3. Grafana Dashboard

Import the provided Grafana dashboard configuration for comprehensive monitoring.

## Security Considerations

### 1. Network Security

- Use VPN or private networks
- Restrict database access
- Enable firewall rules
- Use TLS/SSL for all connections

### 2. Secret Management

- Use Kubernetes secrets or external secret managers
- Rotate keys regularly
- Never commit secrets to version control
- Use environment-specific configurations

### 3. Access Control

- Implement RBAC
- Use service accounts
- Monitor access logs
- Enable audit trails

## Backup and Recovery

### 1. Database Backups

```bash
# Automated backup script
#!/bin/bash
pg_dump vantabot > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Configuration Backups

```bash
# Backup configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env config/
```

### 3. Recovery Procedures

1. Restore database from backup
2. Update configuration files
3. Restart services
4. Verify functionality

## Troubleshooting

### Common Issues

**Bot Not Responding:**
- Check Telegram token validity
- Verify network connectivity
- Review application logs

**Database Connection Errors:**
- Verify database credentials
- Check network connectivity
- Ensure database is running

**High Memory Usage:**
- Check for memory leaks
- Adjust resource limits
- Monitor garbage collection

### Log Analysis

```bash
# View application logs
docker-compose logs -f vantabot

# Filter error logs
docker-compose logs vantabot | grep ERROR

# Monitor resource usage
docker stats vantabot
```

### Performance Tuning

**Database Optimization:**
- Add appropriate indexes
- Tune connection pool settings
- Monitor query performance

**Redis Optimization:**
- Adjust memory limits
- Configure eviction policies
- Monitor cache hit rates

## Maintenance

### Regular Tasks

- **Daily**: Monitor logs and metrics
- **Weekly**: Review performance and errors
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and rotate secrets

### Updates and Upgrades

1. Test in staging environment
2. Backup current deployment
3. Deploy new version
4. Monitor for issues
5. Rollback if necessary

## Support

For deployment issues:

- Check the troubleshooting section
- Review application logs
- Contact support: dev@avantis.trading
- Join Discord: [Development Server](https://discord.gg/avantis-trading)
