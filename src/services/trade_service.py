"""
Trade orchestration service - coordinates the complete trading flow.

This service orchestrates the entire trading process:
1. Load addresses/ABIs and validate configuration
2. Pull pair limits and validate parameters
3. Build TradeInput using authoritative scaling
4. Validate against on-chain limits
5. Execute staticcall validation
6. Send transaction and log results
"""

import json
import logging
from decimal import Decimal
from typing import Any, Optional

from ..adapters.pyth_feed import PythFeedAdapter
from ..adapters.web3_trading import Web3TradingAdapter
from ..core.math import to_trade_units
from ..core.models import (
    ContractStatus,
    HumanTradeParams,
    RiskLimits,
    TradeInput,
    TradeLimits,
    TradeResult,
    WalletInfo,
)
from ..core.validation import comprehensive_validation

logger = logging.getLogger(__name__)


class TradeService:
    """Orchestrates the complete trading flow with proper validation."""

    def __init__(
        self, rpc_url: str, private_key: str, network_config_path: Optional[str] = None
    ):
        """
        Initialize trade service.

        Args:
            rpc_url: RPC endpoint URL
            private_key: Private key for signing transactions
            network_config_path: Path to network configuration file
        """
        self.rpc_url = rpc_url
        self.private_key = private_key

        # Load network configuration
        if network_config_path is None:
            network_config_path = "config/addresses/base.mainnet.json"

        self.network_config = self._load_network_config(network_config_path)
        self._validate_network_config()

        # Initialize adapters
        self.web3_adapter = Web3TradingAdapter(
            rpc_url=rpc_url,
            private_key=private_key,
            trading_address=self.network_config["contracts"]["trading"]["address"],
        )

        # Initialize price feed adapter
        pyth_config = self.network_config.get("oracles", {}).get("pyth", {})
        if pyth_config.get("hermesEndpoint"):
            self.pyth_adapter = PythFeedAdapter(
                hermes_endpoint=pyth_config["hermesEndpoint"],
                ws_url=pyth_config.get("wsUrl"),
            )
        else:
            self.pyth_adapter = None

        # Load risk limits from configuration
        self.risk_limits = self._load_risk_limits()

        logger.info("Trade Service initialized")
        logger.info(f"  Network: {self.network_config['network']}")
        logger.info(
            f"  Trading Contract: {self.network_config['contracts']['trading']['address']}"
        )

    def _load_network_config(self, config_path: str) -> dict[str, Any]:
        """Load network configuration from JSON file."""
        try:
            with open(config_path) as f:
                config = json.load(f)

            # Check for deprecated addresses
            if config.get("deprecated", False):
                raise ValueError(
                    f"Network configuration is deprecated: {config.get('warning', 'Unknown reason')}. "
                    f"Please update to use: {config.get('replacement', 'new configuration')}"
                )

            return config

        except FileNotFoundError:
            raise FileNotFoundError(f"Network configuration not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in network configuration: {e}")

    def _validate_network_config(self) -> None:
        """Validate network configuration."""
        required_fields = ["network", "chainId", "contracts"]
        for field in required_fields:
            if field not in self.network_config:
                raise ValueError(f"Missing required field in network config: {field}")

        required_contracts = ["trading"]
        contracts = self.network_config["contracts"]
        for contract in required_contracts:
            if contract not in contracts:
                raise ValueError(
                    f"Missing required contract in network config: {contract}"
                )

    def _load_risk_limits(self) -> RiskLimits:
        """Load risk management limits from configuration."""
        # Default risk limits - these should be configurable
        return RiskLimits(
            max_position_size_usd=Decimal("100000"),  # $100k max position
            max_account_risk_pct=Decimal("0.10"),  # 10% max account risk
            liquidation_buffer_pct=Decimal("0.05"),  # 5% liquidation buffer
            max_daily_loss_pct=Decimal("0.20"),  # 20% max daily loss
        )

    def get_contract_status(self) -> ContractStatus:
        """Get current contract status."""
        return self.web3_adapter.get_contract_status()

    def get_wallet_info(self) -> WalletInfo:
        """Get current wallet information."""
        return self.web3_adapter.get_wallet_info()

    def get_contract_limits(self) -> TradeLimits:
        """Get contract trading limits."""
        limits_dict = self.web3_adapter.get_contract_limits()

        return TradeLimits(
            minPositionSize=limits_dict["min_position_size"],
            maxPositionSize=limits_dict["max_position_size"],
            maxLeverage=limits_dict["max_leverage"],
            maxSlippage=limits_dict["max_slippage"],
            maxPairs=limits_dict["max_pairs"],
        )

    def validate_trade_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate that all preconditions for trading are met.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check contract status
            status = self.get_contract_status()
            if status.is_paused:
                return False, "Trading is currently paused"

            # Check wallet connection
            wallet_info = self.get_wallet_info()
            if not wallet_info.is_connected:
                return False, "Wallet not connected"

            # Check minimum balances
            if wallet_info.eth_balance < Decimal("0.001"):
                return False, "Insufficient ETH for gas fees"

            if wallet_info.usdc_balance < Decimal("1"):
                return False, "Insufficient USDC balance"

            return True, None

        except Exception as e:
            logger.error(f"Precondition validation failed: {e}")
            return False, str(e)

    async def open_market_trade(
        self, params: HumanTradeParams, dry_run: bool = True
    ) -> TradeResult:
        """
        Open a market trade with complete validation and orchestration.

        Args:
            params: Human-readable trade parameters
            dry_run: If True, only perform staticcall validation

        Returns:
            TradeResult with transaction details or error information
        """
        logger.info("Starting market trade orchestration")
        logger.info(f"  Collateral: ${params.collateral_usdc}")
        logger.info(f"  Leverage: {params.leverage_x}x")
        logger.info(f"  Slippage: {params.slippage_pct}%")
        logger.info(f"  Pair: {params.pair_index}")
        logger.info(f"  Direction: {'LONG' if params.is_long else 'SHORT'}")
        logger.info(f"  Dry Run: {dry_run}")

        try:
            # 1. Validate preconditions
            is_valid, error_msg = self.validate_trade_preconditions()
            if not is_valid:
                return TradeResult(
                    success=False,
                    transaction_hash=None,
                    error_message=f"Precondition validation failed: {error_msg}",
                    gas_used=None,
                    block_number=None,
                )

            # 2. Get contract limits
            limits = self.get_contract_limits()

            # 3. Get wallet info for risk validation (skip if RPC rate limited)
            try:
                wallet_info = self.get_wallet_info()
                current_balance = wallet_info.usdc_balance
            except Exception as e:
                logger.warning(f"Could not get wallet info: {e}, using default balance")
                current_balance = Decimal("10000")  # Default balance for validation

            # 4. Comprehensive validation and clamping
            is_valid, errors, clamped_params = comprehensive_validation(
                params, limits, self.risk_limits, current_balance
            )

            if not is_valid:
                return TradeResult(
                    success=False,
                    transaction_hash=None,
                    error_message=f"Validation failed: {'; '.join(errors)}",
                    gas_used=None,
                    block_number=None,
                )

            # 5. Convert to trade units using authoritative scaling
            trade_units = to_trade_units(
                clamped_params.collateral_usdc,
                clamped_params.leverage_x,
                clamped_params.slippage_pct,
            )

            # 6. Build trade input
            trade_input: TradeInput = {
                "pairIndex": clamped_params.pair_index,
                "buy": clamped_params.is_long,
                "leverage": trade_units.leverage,
                "initialPosToken": trade_units.initial_pos_token,
                "positionSizeUSDC": trade_units.position_size_usdc,
                "openPrice": 0,  # Market order
                "tp": 0,  # No take profit
                "sl": 0,  # No stop loss
                "timestamp": 0,  # Current timestamp
            }

            # 7. Staticcall validation
            staticcall_success, staticcall_error = self.web3_adapter.staticcall_trade(
                trade_input, order_type=0, slippage=trade_units.slippage
            )

            if not staticcall_success:
                return TradeResult(
                    success=False,
                    transaction_hash=None,
                    error_message=f"Staticcall validation failed: {staticcall_error}",
                    gas_used=None,
                    block_number=None,
                )

            logger.info("✅ Staticcall validation passed - trade parameters are valid")

            # 8. Execute trade if not dry run
            if dry_run:
                logger.info("Dry run completed successfully - trade would execute")
                return TradeResult(
                    success=True,
                    transaction_hash="DRY_RUN",
                    error_message=None,
                    gas_used=None,
                    block_number=None,
                )
            else:
                # Send actual transaction
                result = self.web3_adapter.send_trade(
                    trade_input, order_type=0, slippage=trade_units.slippage
                )

                if result.success:
                    logger.info("🎉 Trade executed successfully!")
                    self._log_trade_success(result, trade_input, trade_units)
                else:
                    logger.error(f"❌ Trade execution failed: {result.error_message}")

                return result

        except Exception as e:
            logger.error(f"Trade orchestration failed: {e}")
            return TradeResult(
                success=False,
                transaction_hash=None,
                error_message=f"Trade orchestration failed: {str(e)}",
                gas_used=None,
                block_number=None,
            )

    def _log_trade_success(
        self, result: TradeResult, trade_input: TradeInput, trade_units: Any
    ) -> None:
        """Log successful trade details."""
        logger.info("=" * 60)
        logger.info("TRADE EXECUTION SUCCESS")
        logger.info("=" * 60)
        logger.info(f"Transaction Hash: {result.transaction_hash}")
        logger.info(f"BaseScan URL: https://basescan.org/tx/{result.transaction_hash}")
        logger.info(f"Block Number: {result.block_number}")
        logger.info(f"Gas Used: {result.gas_used}")
        logger.info("")
        logger.info("Trade Parameters:")
        logger.info(f"  Pair Index: {trade_input['pairIndex']}")
        logger.info(f"  Direction: {'LONG' if trade_input['buy'] else 'SHORT'}")
        logger.info(f"  Leverage: {trade_input['leverage']} (1e10 scale)")
        logger.info(f"  Initial Position: {trade_input['initialPosToken']} (USDC 6dp)")
        logger.info(f"  Position Size: {trade_input['positionSizeUSDC']} (USDC 6dp)")
        logger.info(f"  Open Price: {trade_input['openPrice']} (market order)")
        logger.info("")
        logger.info("Scaled Parameters:")
        logger.info(f"  Initial Position Token: {trade_units.initial_pos_token}")
        logger.info(f"  Leverage: {trade_units.leverage}")
        logger.info(f"  Position Size USDC: {trade_units.position_size_usdc}")
        logger.info(f"  Slippage: {trade_units.slippage}")
        logger.info("=" * 60)

    async def get_current_price(self, pair_index: int) -> Optional[Decimal]:
        """
        Get current price for a trading pair.

        Args:
            pair_index: Trading pair index

        Returns:
            Current price or None if unavailable
        """
        if not self.pyth_adapter:
            logger.warning("Price feed adapter not available")
            return None

        try:
            # Map pair index to Pyth pair ID
            pair_mapping = {
                0: "crypto.BTC/USD",
                1: "crypto.ETH/USD",
                2: "crypto.SOL/USD",
            }

            pyth_pair_id = pair_mapping.get(pair_index)
            if not pyth_pair_id:
                logger.warning(f"No price feed mapping for pair index {pair_index}")
                return None

            async with self.pyth_adapter as adapter:
                price_info = await adapter.get_latest_prices([pyth_pair_id])
                if pyth_pair_id in price_info:
                    return price_info[pyth_pair_id].price

            return None

        except Exception as e:
            logger.error(f"Failed to get current price for pair {pair_index}: {e}")
            return None
