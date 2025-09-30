#!/usr/bin/env python3
"""Validate staging/production canary configuration against security gates.

Usage:
    python scripts/validate_canary_config.py .env.staging.canary
    python scripts/validate_canary_config.py .env.production.canary
"""

import os
import sys
from pathlib import Path


class ConfigValidator:
    """Validate canary configuration."""

    REQUIRED_VARS = {
        "ENVIRONMENT": ["production", "prod"],
        "EXEC_MODE": ["DRY", "LIVE"],
        "DATABASE_URL": None,  # Any value OK
        "REDIS_URL": None,
        "BASE_RPC_URL": None,
        "SIGNER_BACKEND": ["kms", "local"],
        "ALLOW_LIVE_AFTER_STREAK": ["3"],
    }

    CANARY_SAFETY_VARS = {
        "MAX_NOTIONAL_USDC": 10,  # Max value for canary
        "MAX_LEVERAGE": 2,  # Max value for canary
        "ALLOWED_SYMBOLS": ["BTC,ETH", "BTC", "ETH"],  # Only these combos
        "CANARY_ENABLED": ["true", "True", "TRUE"],
    }

    SECURITY_VARS = {
        "ENABLE_RBF": ["true", "True", "TRUE", "false", "False", "FALSE"],
        "LOG_LEVEL": ["INFO", "DEBUG", "WARNING"],
        "METRICS_ENABLED": ["true", "True", "TRUE"],
    }

    FORBIDDEN_VARS = {
        "TRADER_PRIVATE_KEY": "❌ CRITICAL: Private keys must not be in config files!",
        "AWS_SECRET_ACCESS_KEY": "❌ CRITICAL: AWS secrets must not be in config files!",
    }

    def __init__(self, config_path: Path, mode: str = "canary"):
        """Initialize validator.

        Args:
            config_path: Path to .env file
            mode: "canary" for strict canary validation, "production" for production
        """
        self.config_path = config_path
        self.mode = mode
        self.config = {}
        self.errors = []
        self.warnings = []
        self.info = []

    def load_config(self) -> bool:
        """Load configuration from file."""
        if not self.config_path.exists():
            self.errors.append(f"Config file not found: {self.config_path}")
            return False

        try:
            with open(self.config_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # Strip comments
                        if "#" in value:
                            value = value.split("#")[0]
                        self.config[key.strip()] = value.strip().strip('"').strip("'")
            return True
        except Exception as e:
            self.errors.append(f"Failed to load config: {e}")
            return False

    def validate_required_vars(self):
        """Validate required variables are present and valid."""
        for var, allowed_values in self.REQUIRED_VARS.items():
            if var not in self.config:
                self.errors.append(f"❌ Missing required variable: {var}")
                continue

            value = self.config[var]

            # Check against allowed values if specified
            if allowed_values and value not in allowed_values:
                self.errors.append(
                    f"❌ {var}={value} - Expected one of: {', '.join(allowed_values)}"
                )
            else:
                self.info.append(f"✅ {var}={value}")

    def validate_canary_safety(self):
        """Validate canary safety caps are enforced."""
        if self.mode != "canary":
            return

        # Check EXEC_MODE
        exec_mode = self.config.get("EXEC_MODE", "").upper()
        if exec_mode == "LIVE":
            self.warnings.append(
                "⚠️  EXEC_MODE=LIVE - Ensure this is intentional for canary!"
            )

        # Check MAX_NOTIONAL_USDC
        max_notional = self.config.get("MAX_NOTIONAL_USDC")
        if max_notional:
            try:
                notional_value = float(max_notional)
                if notional_value > self.CANARY_SAFETY_VARS["MAX_NOTIONAL_USDC"]:
                    self.errors.append(
                        f"❌ MAX_NOTIONAL_USDC={notional_value} exceeds canary limit of "
                        f"{self.CANARY_SAFETY_VARS['MAX_NOTIONAL_USDC']}"
                    )
                else:
                    self.info.append(f"✅ MAX_NOTIONAL_USDC={notional_value} (safe)")
            except ValueError:
                self.errors.append(
                    f"❌ MAX_NOTIONAL_USDC={max_notional} is not a valid number"
                )
        else:
            self.warnings.append("⚠️  MAX_NOTIONAL_USDC not set - unlimited notional!")

        # Check MAX_LEVERAGE
        max_leverage = self.config.get("MAX_LEVERAGE")
        if max_leverage:
            try:
                leverage_value = int(max_leverage)
                if leverage_value > self.CANARY_SAFETY_VARS["MAX_LEVERAGE"]:
                    self.errors.append(
                        f"❌ MAX_LEVERAGE={leverage_value} exceeds canary limit of "
                        f"{self.CANARY_SAFETY_VARS['MAX_LEVERAGE']}"
                    )
                else:
                    self.info.append(f"✅ MAX_LEVERAGE={leverage_value} (safe)")
            except ValueError:
                self.errors.append(
                    f"❌ MAX_LEVERAGE={max_leverage} is not a valid integer"
                )
        else:
            self.warnings.append("⚠️  MAX_LEVERAGE not set - unlimited leverage!")

        # Check ALLOWED_SYMBOLS
        allowed_symbols = self.config.get("ALLOWED_SYMBOLS", "")
        if allowed_symbols:
            if allowed_symbols not in self.CANARY_SAFETY_VARS["ALLOWED_SYMBOLS"]:
                symbols = allowed_symbols.split(",")
                if len(symbols) > 2:
                    self.warnings.append(
                        f"⚠️  ALLOWED_SYMBOLS has {len(symbols)} symbols - "
                        f"canary should start with 2 (BTC,ETH)"
                    )
                else:
                    self.info.append(f"✅ ALLOWED_SYMBOLS={allowed_symbols}")
            else:
                self.info.append(f"✅ ALLOWED_SYMBOLS={allowed_symbols}")
        else:
            self.warnings.append("⚠️  ALLOWED_SYMBOLS not set - all symbols allowed!")

        # Check CANARY_ENABLED
        canary_enabled = self.config.get("CANARY_ENABLED", "").lower()
        if canary_enabled not in ["true", "1", "yes"]:
            self.warnings.append(
                "⚠️  CANARY_ENABLED not set to true - canary mode not explicitly marked"
            )

    def validate_security(self):
        """Validate security-related settings."""
        # Check ENVIRONMENT blocks mock prices
        environment = self.config.get("ENVIRONMENT", "").lower()
        if environment not in ["production", "prod", "staging"]:
            self.errors.append(
                f"❌ ENVIRONMENT={environment} will NOT block mock prices! "
                f"Must be 'production', 'prod', or 'staging'"
            )
        else:
            self.info.append(
                f"✅ ENVIRONMENT={environment} (mock prices blocked)"
            )

        # Check SIGNER_BACKEND
        signer_backend = self.config.get("SIGNER_BACKEND", "").lower()
        if signer_backend == "local" and self.mode == "canary":
            self.warnings.append(
                "⚠️  SIGNER_BACKEND=local - Production should use 'kms'"
            )
        elif signer_backend == "kms":
            # Check KMS vars present
            if "AWS_KMS_KEY_ID" not in self.config:
                self.errors.append("❌ SIGNER_BACKEND=kms but AWS_KMS_KEY_ID not set")
            if "AWS_REGION" not in self.config:
                self.warnings.append(
                    "⚠️  AWS_REGION not set - will default to us-east-1"
                )

        # Check circuit breaker settings
        streak_required = self.config.get("ALLOW_LIVE_AFTER_STREAK", "0")
        try:
            streak_value = int(streak_required)
            if streak_value < 3:
                self.warnings.append(
                    f"⚠️  ALLOW_LIVE_AFTER_STREAK={streak_value} - "
                    f"Recommended: 3 (circuit breaker)"
                )
            else:
                self.info.append(f"✅ ALLOW_LIVE_AFTER_STREAK={streak_value}")
        except ValueError:
            self.errors.append(
                f"❌ ALLOW_LIVE_AFTER_STREAK={streak_required} is not a valid integer"
            )

        # Check RBF enabled
        rbf_enabled = self.config.get("ENABLE_RBF", "false").lower()
        if rbf_enabled in ["true", "1", "yes"]:
            self.info.append("✅ ENABLE_RBF=true (transaction retry enabled)")
        else:
            self.warnings.append(
                "⚠️  ENABLE_RBF not enabled - stuck transactions won't retry"
            )

        # Check metrics enabled
        metrics_enabled = self.config.get("METRICS_ENABLED", "false").lower()
        if metrics_enabled not in ["true", "1", "yes"]:
            self.errors.append(
                "❌ METRICS_ENABLED not true - required for monitoring!"
            )

    def validate_forbidden_vars(self):
        """Check for forbidden variables (secrets in plaintext)."""
        for var, message in self.FORBIDDEN_VARS.items():
            if var in self.config:
                self.errors.append(f"{message} Found: {var}")

    def validate(self) -> bool:
        """Run all validations.

        Returns:
            True if validation passed (no errors), False otherwise
        """
        if not self.load_config():
            return False

        self.validate_required_vars()
        self.validate_canary_safety()
        self.validate_security()
        self.validate_forbidden_vars()

        return len(self.errors) == 0

    def print_report(self):
        """Print validation report."""
        print("\n" + "=" * 70)
        print(f"📋 CONFIGURATION VALIDATION: {self.config_path.name}")
        print(f"Mode: {self.mode.upper()}")
        print("=" * 70 + "\n")

        if self.errors:
            print("🔴 ERRORS (blocking):")
            for error in self.errors:
                print(f"  {error}")
            print()

        if self.warnings:
            print("🟡 WARNINGS (review):")
            for warning in self.warnings:
                print(f"  {warning}")
            print()

        if self.info:
            print("✅ PASSED:")
            for info in self.info:
                print(f"  {info}")
            print()

        print("=" * 70)
        if self.errors:
            print("❌ VALIDATION FAILED - Fix errors before deployment")
            print("=" * 70)
            return False
        elif self.warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS - Review before deployment")
            print("=" * 70)
            return True
        else:
            print("✅ VALIDATION PASSED - Configuration is safe")
            print("=" * 70)
            return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_canary_config.py <config_file>")
        print("\nExample:")
        print("  python scripts/validate_canary_config.py .env.staging.canary")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    
    # Determine mode from filename
    mode = "canary" if "canary" in config_path.name.lower() else "production"
    
    validator = ConfigValidator(config_path, mode=mode)
    passed = validator.validate()
    validator.print_report()

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

