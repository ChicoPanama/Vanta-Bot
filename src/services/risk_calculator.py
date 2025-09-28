from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Any, Dict, List, Optional

# NOTE: This module does not restrict. It computes and explains.

class RiskLevel(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    EXTREME = "extreme"

@dataclass
class RiskEducationCfg:
    conservative_account_risk: Decimal = Decimal("0.02")  # 2% edu threshold
    moderate_account_risk: Decimal = Decimal("0.05")      # 5%
    aggressive_account_risk: Decimal = Decimal("0.10")    # 10%

    warn_leverage_high: Decimal = Decimal("50")
    warn_leverage_extreme: Decimal = Decimal("200")
    warn_liq_distance: Decimal = Decimal("0.01")  # 1%
    stress_move: Decimal = Decimal("0.02")        # 2% move scenario (edu)

class RiskCalculator:
    """Risk education (non-blocking)."""

    def __init__(self, cfg: Optional[RiskEducationCfg] = None):
        self.cfg = cfg or RiskEducationCfg()
    # Expose enum on instance/class for tests expecting calc._level.__self__.RiskLevel
    RiskLevel = RiskLevel

    async def analyze(
        self,
        *,
        position_size_usd: Decimal,
        leverage: Decimal,
        account_balance_usd: Decimal,
        asset: str,
        protocol_max_leverage: Optional[int] = 500
    ) -> Dict[str, Any]:
        # Technical validations (only impossibilities)
        if position_size_usd <= 0 or leverage <= 0 or account_balance_usd <= 0:
            raise ValueError("Position size, leverage, and account balance must be positive.")

        margin_required = position_size_usd / leverage
        if margin_required >= account_balance_usd:
            raise ValueError(f"Insufficient balance: need ${margin_required:,.2f}, have ${account_balance_usd:,.2f}")

        # Heuristic liquidation distance (educational; protocol may differ)
        liq_distance_pct = Decimal("1") / leverage

        # Scenario table (0.5%, 1%, cfg.stress_move, 5%, 10%)
        # Use notional (position size times leverage) for loss scenarios
        scenarios = self._scenarios(position_size_usd * leverage, account_balance_usd)

        # "Account risk %" under stress case
        stress = scenarios["stress_move"]
        account_risk_pct = stress["loss"] / account_balance_usd if account_balance_usd > 0 else Decimal("0")

        level = self._level(account_risk_pct)
        warnings = self._warnings(leverage, account_risk_pct, liq_distance_pct, protocol_max_leverage)
        quality = self._quality(leverage, account_risk_pct, liq_distance_pct)

        return {
            "asset": asset,
            "margin_required": margin_required,
            "liq_distance_pct": liq_distance_pct,
            "account_risk_pct": account_risk_pct,
            "risk_level": level.value,
            "scenarios": scenarios,
            "educational_warnings": warnings,
            "position_quality": quality,
            "can_execute": True,  # always true unless technical impossible
            "leverage_category": self._lev_cat(leverage),
            "protocol_max_leverage": protocol_max_leverage,
        }

    def _scenarios(self, size: Decimal, equity: Decimal) -> Dict[str, Dict[str, Any]]:
        def mk(move: Decimal):
            loss = (size * move).quantize(Decimal("0.01"))
            impact = (loss / equity).quantize(Decimal("0.0001")) if equity else Decimal("0")
            return {"move_pct": move, "loss": loss, "account_impact_pct": impact}

        return {
            "move_0_5": mk(Decimal("0.005")),
            "move_1_0": mk(Decimal("0.01")),
            "stress_move": mk(self.cfg.stress_move),
            "crash_5": mk(Decimal("0.05")),
            "black_swan_10": mk(Decimal("0.10")),
        }

    def _level(self, account_risk_pct: Decimal) -> RiskLevel:
        if account_risk_pct >= self.cfg.aggressive_account_risk:
            return RiskLevel.EXTREME
        if account_risk_pct >= self.cfg.moderate_account_risk:
            return RiskLevel.AGGRESSIVE
        if account_risk_pct >= self.cfg.conservative_account_risk:
            return RiskLevel.MODERATE
        return RiskLevel.CONSERVATIVE

    def _lev_cat(self, lev: Decimal) -> str:
        if lev >= 200:
            return "Ultra-High (200x+)"
        if lev >= 100:
            return "Very High (100-199x)"
        if lev >= 50:
            return "High (50-99x)"
        if lev >= 10:
            return "Moderate (10-49x)"
        return "Conservative (<10x)"

    def _warnings(
        self,
        lev: Decimal,
        account_risk_pct: Decimal,
        liq_dist_pct: Decimal,
        protocol_max_leverage: Optional[int],
    ) -> List[Dict[str, str]]:
        w: List[Dict[str, str]] = []
        if protocol_max_leverage:
            w.append({
                "type": "protocol",
                "title": "Protocol Capability",
                "message": f"Avantis supports up to ~{protocol_max_leverage}x on some markets. This is information—not a target.",
                "severity": "low",
            })
        if lev >= self.cfg.warn_leverage_extreme:
            w.append({
                "type": "lev_extreme",
                "title": "Ultra-High Leverage",
                "message": f"{lev}x greatly amplifies PnL. A ~{(Decimal('1')/lev):.2%} move can liquidate.",
                "severity": "high",
            })
        elif lev >= self.cfg.warn_leverage_high:
            w.append({
                "type": "lev_high",
                "title": "High Leverage",
                "message": f"{lev}x leverage increases both gains and losses. Monitor closely.",
                "severity": "medium",
            })
        if account_risk_pct >= Decimal("0.20"):
            w.append({
                "type": "acct_very_high",
                "title": "Very High Account Risk",
                "message": f"Stress scenario risks ~{account_risk_pct:.1%} of equity.",
                "severity": "high",
            })
        elif account_risk_pct >= Decimal("0.10"):
            w.append({
                "type": "acct_high",
                "title": "High Account Risk",
                "message": f"Stress scenario risks ~{account_risk_pct:.1%} of equity.",
                "severity": "medium",
            })
        if liq_dist_pct <= self.cfg.warn_liq_distance:
            w.append({
                "type": "liq_close",
                "title": "Close to Liquidation",
                "message": f"Estimated distance ~{liq_dist_pct:.2%}. Small adverse moves can liquidate.",
                "severity": "medium" if liq_dist_pct > Decimal("0.005") else "high",
            })
        return w

    def _quality(self, lev: Decimal, acct_risk: Decimal, liq_d: Decimal) -> Dict[str, Any]:
        score = 100
        if lev > 100: 
            score -= 30
        elif lev > 50: 
            score -= 15
        elif lev > 25: 
            score -= 5

        if acct_risk > Decimal("0.10"): 
            score -= 25
        elif acct_risk > Decimal("0.05"): 
            score -= 10

        if liq_d < Decimal("0.01"): 
            score -= 20
        elif liq_d < Decimal("0.02"): 
            score -= 10

        score = max(0, score)
        if score >= 80: 
            rating, desc = "Excellent", "Conservative risk profile with good safety margins."
        elif score >= 60: 
            rating, desc = "Good", "Moderate risk with reasonable safety margins."
        elif score >= 40: 
            rating, desc = "Risky", "High risk—monitor closely."
        else: 
            rating, desc = "Very Risky", "Extreme risk—minimal safety margin."

        return {"score": score, "rating": rating, "description": desc}

risk_calculator = RiskCalculator()
