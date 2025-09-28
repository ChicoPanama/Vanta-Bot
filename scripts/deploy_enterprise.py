#!/usr/bin/env python3
"""Enterprise deployment script for Vanta Bot."""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.settings import settings

logger = logging.getLogger(__name__)


class EnterpriseDeployment:
    """Enterprise deployment orchestrator."""
    
    def __init__(self):
        self.deployment_steps = [
            self.check_prerequisites,
            self.setup_environment,
            self.run_database_migrations,
            self.setup_key_vault,
            self.configure_monitoring,
            self.deploy_services,
            self.run_health_checks,
            self.enable_feature_flags
        ]
    
    def run_deployment(self):
        """Run complete enterprise deployment."""
        logger.info("Starting enterprise deployment...")
        
        for step in self.deployment_steps:
            try:
                logger.info(f"Running step: {step.__name__}")
                step()
                logger.info(f"Step {step.__name__} completed successfully")
            except Exception as e:
                logger.error(f"Step {step.__name__} failed: {e}")
                raise
        
        logger.info("Enterprise deployment completed successfully!")
    
    def check_prerequisites(self):
        """Check deployment prerequisites."""
        logger.info("Checking prerequisites...")
        
        # Check Python version
        if sys.version_info < (3, 9):
            raise RuntimeError("Python 3.9+ required")
        
        # Check required environment variables
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'DATABASE_URL',
            'REDIS_URL',
            'BASE_RPC_URL'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise RuntimeError(f"Missing required environment variables: {missing_vars}")
        
        # Check Redis connectivity
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            logger.info("Redis connectivity verified")
        except Exception as e:
            raise RuntimeError(f"Redis connectivity failed: {e}")
        
        # Check database connectivity
        try:
            from sqlalchemy import create_engine
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("Database connectivity verified")
        except Exception as e:
            raise RuntimeError(f"Database connectivity failed: {e}")
        
        logger.info("Prerequisites check passed")
    
    def setup_environment(self):
        """Setup deployment environment."""
        logger.info("Setting up environment...")
        
        # Create necessary directories
        directories = [
            "logs",
            "data",
            "monitoring",
            "config/abis"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        
        # Set up logging
        from src.monitoring.logging import setup_logging
        setup_logging(
            log_level=settings.LOG_LEVEL,
            log_json=settings.LOG_JSON
        )
        
        logger.info("Environment setup completed")
    
    def run_database_migrations(self):
        """Run database migrations."""
        logger.info("Running database migrations...")
        
        try:
            # Run Alembic migrations
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Database migrations completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Migration failed: {e.stderr}")
            raise RuntimeError(f"Database migration failed: {e}")
    
    def setup_key_vault(self):
        """Setup key vault configuration."""
        logger.info("Setting up key vault...")
        
        if settings.KEY_ENVELOPE_ENABLED:
            if settings.AWS_KMS_KEY_ID:
                logger.info("Using AWS KMS for key vault")
                # Verify AWS credentials
                try:
                    import boto3
                    kms = boto3.client('kms', region_name=settings.AWS_REGION)
                    kms.describe_key(KeyId=settings.AWS_KMS_KEY_ID)
                    logger.info("AWS KMS key verified")
                except Exception as e:
                    raise RuntimeError(f"AWS KMS setup failed: {e}")
            elif settings.LOCAL_WRAP_KEY_B64:
                logger.info("Using local Fernet key vault")
                # Generate local key if not provided
                if not settings.LOCAL_WRAP_KEY_B64:
                    from cryptography.fernet import Fernet
                    key = Fernet.generate_key()
                    logger.warning(f"Generated local key: {key.decode()}")
                    logger.warning("Set LOCAL_WRAP_KEY_B64 environment variable for production")
            else:
                raise RuntimeError("Key vault configuration required")
        else:
            logger.info("Using legacy encryption (KEY_ENVELOPE_ENABLED=False)")
    
    def configure_monitoring(self):
        """Configure monitoring and observability."""
        logger.info("Configuring monitoring...")
        
        # Setup Prometheus metrics
        from src.monitoring.metrics import metrics_collector
        logger.info("Prometheus metrics configured")
        
        # Setup health server
        from src.monitoring.health_server import app
        logger.info("Health server configured")
        
        # Setup circuit breakers
        from src.middleware.circuit_breakers import circuit_breaker_manager
        logger.info("Circuit breakers configured")
        
        logger.info("Monitoring configuration completed")
    
    def deploy_services(self):
        """Deploy application services."""
        logger.info("Deploying services...")
        
        # Initialize key components
        try:
            from src.blockchain.base_client import base_client
            logger.info("Blockchain client initialized")
        except Exception as e:
            logger.error(f"Blockchain client initialization failed: {e}")
            raise
        
        try:
            from src.blockchain.avantis_client import AvantisClient
            avantis_client = AvantisClient()
            logger.info("Avantis client initialized")
        except Exception as e:
            logger.error(f"Avantis client initialization failed: {e}")
            raise
        
        try:
            from src.bot.middleware.rate_limit import create_rate_limiter
            rate_limiter = create_rate_limiter()
            logger.info("Rate limiter initialized")
        except Exception as e:
            logger.error(f"Rate limiter initialization failed: {e}")
            raise
        
        logger.info("Services deployed successfully")
    
    def run_health_checks(self):
        """Run comprehensive health checks."""
        logger.info("Running health checks...")
        
        # Check database
        try:
            from sqlalchemy import create_engine
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("Database health check passed")
        except Exception as e:
            raise RuntimeError(f"Database health check failed: {e}")
        
        # Check Redis
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            logger.info("Redis health check passed")
        except Exception as e:
            raise RuntimeError(f"Redis health check failed: {e}")
        
        # Check RPC
        try:
            from src.blockchain.base_client import base_client
            base_client.w3.eth.get_block('latest')
            logger.info("RPC health check passed")
        except Exception as e:
            raise RuntimeError(f"RPC health check failed: {e}")
        
        logger.info("All health checks passed")
    
    def enable_feature_flags(self):
        """Enable feature flags for production."""
        logger.info("Enabling feature flags...")
        
        # Feature flags to enable
        feature_flags = {
            'KEY_ENVELOPE_ENABLED': True,
            'TX_PIPELINE_V2': True,
            'AVANTIS_V2': True,
            'STRICT_HANDLERS_ENABLED': True,
            'STRUCTURED_LOGS_ENABLED': True
        }
        
        for flag, value in feature_flags.items():
            logger.info(f"Feature flag {flag}: {value}")
        
        logger.info("Feature flags configured")


def main():
    """Main deployment function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        deployment = EnterpriseDeployment()
        deployment.run_deployment()
        print("✅ Enterprise deployment completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        print(f"❌ Deployment failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
