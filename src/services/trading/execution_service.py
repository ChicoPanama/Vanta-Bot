from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.bot.ui.formatting import fmt_usd
from src.services.copy_trading.execution_mode import execution_manager
from src.services.trading.trade_drafts import TradeDraft
from src.utils.obs import log_exc, rid
from src.utils.resilience import CircuitBreaker, guarded_call

log = logging.getLogger("vanta.exec")

# Try to use your Avantis SDK wrapper if present; otherwise fallback
try:
    from src.integrations.avantis.sdk_client import (
        asset_parameters,
        ensure_allowance,
        fee_parameters,
        get_allowance,
        get_trader_client,
        pairs_cache,
        tokens,
        trading_parameters,
    )

    SDK_AVAILABLE = True
except Exception as e:
    log.warning(f"Avantis SDK import failed: {e}")
    SDK_AVAILABLE = False


@dataclass
class QuoteResult:
    ok: bool
    message: str
    data: dict[str, Any] | None = None


SLIPPAGE_STEPS = [Decimal("0.5"), Decimal("1"), Decimal("2")]  # percent choices


class ExecutionService:
    """
    Phase 3: Quote + slippage + USDC allowance.
    Phase 4 will add execute_open/execute_close.
    """

    def __init__(self, settings):
        self.settings = settings
        self.breaker = CircuitBreaker(fail_threshold=5, reset_after=20.0)

    async def _guard(self, label: str, fn):
        req = rid()
        try:
            res = await guarded_call(self.breaker, fn, timeout_s=8.0, retries=2)
            log.info("ok", extra={"extra": {"op": label, "req": req}})
            return res
        except Exception as e:
            log_exc(e, {"op": label, "req": req})
            raise

    # --------------- High-level API ----------------

    async def quote_from_draft(
        self,
        draft: TradeDraft,
        slippage_pct: Decimal | None = None,
    ) -> QuoteResult:
        """
        Build a trade input from the draft and compute fees/protection/spreads.
        """
        if draft is None or not draft.pair:
            return QuoteResult(False, "No draft or pair selected")

        # basic input checks
        if not draft.side or draft.leverage is None or draft.collateral_usdc is None:
            return QuoteResult(False, "Please select side, leverage, and collateral")

        # Use configured default slippage when not specified
        if slippage_pct is None:
            slippage_pct = Decimal(str(self.settings.default_slippage_pct or 1))

        # SDK or fallback
        if not SDK_AVAILABLE:
            # Fallback: show a friendly placeholder
            data = {
                "pair": draft.pair,
                "side": draft.side,
                "leverage": str(draft.leverage),
                "collateral_usdc": str(draft.collateral_usdc),
                "slippage_pct": str(slippage_pct),
                "fee_usdc": None,
                "loss_protection": None,
                "pair_spread_bps": None,
                "impact_spread_bps": None,
                "needs_approval": None,
                "allowance": None,
                "usdc_required": str(self._estimate_usdc_required(draft)),
            }
            return QuoteResult(True, "SDK unavailable: showing placeholder quote", data)

        try:
            # Resolve inputs
            pair_symbol = draft.pair
            side = draft.side.upper()  # LONG|SHORT
            leverage = Decimal(draft.leverage)
            collateral = Decimal(draft.collateral_usdc)

            # Estimate notional and minimal USDC requirement for margin
            # (Avantis SDK may consume different fields; adapt as needed)
            notional = collateral * leverage
            usdc_required = collateral  # basic margin assumption

            # Gather parameters from SDK
            pair_info = await self._guard(
                "pairs_cache.get_pair_info",
                lambda: pairs_cache.get_pair_info(pair_symbol),
            )
            base_asset = pair_info.base if hasattr(pair_info, "base") else pair_symbol

            # Fees
            open_fee = await self._guard(
                "fee_parameters.get_opening_fee",
                lambda: fee_parameters.get_opening_fee(pair_symbol, notional, side),
            )

            # Loss protection for the draft trade
            protection = await self._guard(
                "trading_parameters.get_loss_protection",
                lambda: trading_parameters.get_loss_protection_for_trade_input(
                    pair_symbol=pair_symbol,
                    side=side,
                    collateral_usdc=float(collateral),
                    leverage=float(leverage),
                ),
            )

            # Spread & impact
            spread_bps = await self._guard(
                "asset_parameters.get_pair_spread",
                lambda: asset_parameters.get_pair_spread(pair_symbol),
            )
            impact_bps = await self._guard(
                "asset_parameters.get_price_impact",
                lambda: asset_parameters.get_price_impact_spread(
                    pair_symbol, float(notional)
                ),
            )

            # Allowance checks
            usdc = await self._guard("tokens.get_usdc", tokens.get_usdc)
            trader = await self._guard("get_trader_client", get_trader_client)
            owner = await self._guard("trader.get_address", trader.get_address)
            current_allowance = await self._guard(
                "get_allowance",
                lambda: get_allowance(
                    owner, usdc.address, self.settings.trading_contract
                ),
            )
            needs_approval = current_allowance < usdc_required

            data = {
                "pair": pair_symbol,
                "side": side,
                "leverage": str(leverage),
                "collateral_usdc": str(collateral),
                "notional_usd": str(notional),
                "slippage_pct": str(slippage_pct),
                "fee_usdc": str(open_fee) if open_fee is not None else None,
                "loss_protection": protection,  # structure from SDK
                "pair_spread_bps": spread_bps,
                "impact_spread_bps": impact_bps,
                "needs_approval": needs_approval,
                "allowance": str(current_allowance),
                "usdc_required": str(usdc_required),
                "base_asset": base_asset,
            }

            return QuoteResult(True, "OK", data)
        except Exception as e:
            return QuoteResult(False, f"Quote error: {e}")

    async def approve_if_needed(self, usdc_required: Decimal) -> tuple[bool, str]:
        """
        LIVE: send approve tx if allowance insufficient.
        DRY: simulate success.
        """
        if not SDK_AVAILABLE:
            return False, "SDK unavailable; cannot approve."

        try:
            usdc = await tokens.get_usdc()
            trader = await get_trader_client()
            owner = await trader.get_address()
            current_allowance = await get_allowance(
                owner, usdc.address, self.settings.trading_contract
            )

            if current_allowance >= usdc_required:
                return True, "Already approved."

            if not execution_manager.can_execute():
                # DRY: pretend success
                return True, f"DRY mode: would approve {fmt_usd(usdc_required)} USDC."

            # LIVE: approve
            txh = await ensure_allowance(
                owner=owner,
                token_address=usdc.address,
                spender=self.settings.trading_contract,
                amount=float(usdc_required),  # or max allowance if you prefer
            )
            return True, f"Approved {fmt_usd(usdc_required)}. tx={txh}"
        except Exception as e:
            return False, f"Approve error: {e}"

    # --------------- Helpers ----------------

    def _estimate_usdc_required(self, draft: TradeDraft) -> Decimal:
        """
        Margin ~= collateral. Avantis may have additional buffers – Phase 4 can refine per-pair.
        """
        return Decimal(draft.collateral_usdc or 0)

    async def execute_open(
        self,
        draft,
        slippage_pct=None,
    ):
        """
        DRY: simulate success with a fake tx hash
        LIVE: build & send market order using SDK
        Returns (ok: bool, msg: str, result: dict)
        """
        if draft is None or not draft.pair:
            return False, "No draft selected", {}

        if not draft.side or draft.leverage is None or draft.collateral_usdc is None:
            return False, "Draft incomplete. Select side, leverage, collateral.", {}

        if slippage_pct is None:
            slippage_pct = Decimal(str(self.settings.default_slippage_pct or 1))

        # If SDK unavailable, fail gracefully
        if not SDK_AVAILABLE:
            return False, "SDK unavailable: cannot execute.", {}

        try:
            pair_symbol = draft.pair
            side = draft.side.upper()  # LONG|SHORT
            leverage = Decimal(draft.leverage)
            collateral = Decimal(draft.collateral_usdc)
            notional = collateral * leverage

            # Re-get a quote to validate allowance & parameters
            qr = await self.quote_from_draft(draft, slippage_pct)
            if not qr.ok or not qr.data:
                return False, f"Quote failed: {qr.message}", {}

            data = qr.data
            if data.get("needs_approval"):
                return False, "USDC allowance insufficient. Approve first.", {}

            # DRY path: simulate
            if not execution_manager.can_execute():
                fake_hash = "0x" + "d" * 64
                result = {
                    "tx_hash": fake_hash,
                    "mode": "DRY",
                    "pair": pair_symbol,
                    "side": side,
                    "notional": str(notional),
                }
                return True, "DRY: trade executed (simulated).", result

            # LIVE: build + send
            # NOTE: adapt these calls to your SDK wrapper
            trader = await self._guard("get_trader_client", get_trader_client)
            tx_hash = await self._guard(
                "trader.market_open",
                lambda: trader.market_open(
                    pair=pair_symbol,
                    side=side,
                    collateral_usdc=float(collateral),
                    leverage=float(leverage),
                    slippage_pct=float(slippage_pct),
                    order_type="MARKET",  # or MARKET_ZERO_FEE if your strategy qualifies
                ),
            )

            result = {
                "tx_hash": tx_hash,
                "mode": "LIVE",
                "pair": pair_symbol,
                "side": side,
                "notional": str(notional),
            }
            return True, "Trade sent.", result

        except Exception as e:
            return False, f"Execute open error: {e}", {}

    async def get_positions(self):
        """
        Return a list of open positions for the signer (format unified for UI).
        Fallback: empty list when SDK missing.
        """
        if not SDK_AVAILABLE:
            return []

        try:
            trader = await self._guard("get_trader_client", get_trader_client)
            # adapt to your SDK return shape
            positions = await self._guard("trader.get_trades", trader.get_trades)
            normalized = []
            for idx, p in enumerate(positions):
                # heuristics: adjust attributes to your SDK
                pair = getattr(p, "pair", None) or getattr(p, "symbol", "UNKNOWN")
                side = getattr(p, "side", "LONG")
                size = getattr(p, "notional_usd", None) or getattr(p, "size_usd", None)
                lev = getattr(p, "leverage", None)
                entry_px = getattr(p, "entry_price", None)
                pnl = getattr(p, "pnl_usd", None)
                normalized.append(
                    {
                        "index": idx,
                        "pair": str(pair),
                        "side": str(side),
                        "notional_usd": str(size) if size is not None else None,
                        "leverage": str(lev) if lev is not None else None,
                        "entry_px": str(entry_px) if entry_px is not None else None,
                        "pnl_usd": str(pnl) if pnl is not None else None,
                    }
                )
            return normalized
        except Exception as e:
            logger.error(f"Error normalizing positions: {e}")
            return []

    async def execute_close(
        self,
        position_index,
        fraction=Decimal("1"),
    ):
        """
        DRY: simulate closing.
        LIVE: send market close, possibly partial via fraction in [0,1].
        Returns (ok: bool, msg: str, result: dict)
        """
        if not SDK_AVAILABLE:
            return False, "SDK unavailable: cannot close.", {}

        try:
            fraction = Decimal(str(fraction))
            if fraction <= 0 or fraction > 1:
                return False, "Fraction must be between 0 and 1.", {}

            # DRY simulate
            if not execution_manager.can_execute():
                fake_hash = "0x" + "c" * 64
                return (
                    True,
                    "DRY: position closed (simulated).",
                    {"tx_hash": fake_hash, "mode": "DRY"},
                )

            trader = await self._guard("get_trader_client", get_trader_client)
            tx_hash = await self._guard(
                "trader.market_close",
                lambda: trader.market_close(
                    index=int(position_index), fraction=float(fraction)
                ),
            )
            return True, "Close sent.", {"tx_hash": tx_hash, "mode": "LIVE"}
        except Exception as e:
            return False, f"Execute close error: {e}", {}


# Global service accessor (simple DI)
_service: ExecutionService | None = None


def get_execution_service(settings) -> ExecutionService:
    global _service
    if _service is None:
        _service = ExecutionService(settings)
    return _service
