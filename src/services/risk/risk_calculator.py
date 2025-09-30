from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Any

# Light-weight, non-blocking risk education helpers.


@dataclass
class RiskEducation:
    # Educational thresholds (not limits)
    conservative_account_risk: Decimal = Decimal("0.02")  # 2%
    moderate_account_risk: Decimal = Decimal("0.05")  # 5%
    aggressive_account_risk: Decimal = Decimal("0.10")  # 10%

    high_lev_warn: Decimal = Decimal("50")
    extreme_lev_warn: Decimal = Decimal("200")

    # We approximate liquidation distance as 1/leverage for education only.
    # Real engine may include maintenance margin; we label this as approximation.
    liq_proximity_warn: Decimal = Decimal("0.01")  # 1%


class RiskCalculator:
    def __init__(self, education=None):
        self.education = education or RiskEducation()

    def analyze(
        self,
        position_size_usd: Decimal,
        leverage: Decimal,
        account_balance_usd: Decimal,
        asset: str,
    ) -> dict[str, Any]:
        if position_size_usd <= 0:
            raise ValueError("Position size must be positive")
        if leverage <= 0:
            raise ValueError("Leverage must be positive")
        if account_balance_usd <= 0:
            raise ValueError("Account balance must be positive")

        margin_required = position_size_usd / leverage
        if margin_required > account_balance_usd:
            # Technical impossibility for this toy check; still "educational".
            raise ValueError("Insufficient balance for margin (educational check)")

        # Approx liquidation distance (% move against you)
        liq_dist = Decimal("1") / leverage  # approximation, clearly marked in UI

        scenarios = self._scenarios(position_size_usd, account_balance_usd)
        # Handle historical versions where scenario values are strings
        loss_val = scenarios["stress_2pct"]["loss_usd"]
        from decimal import Decimal as _D

        loss_dec = _D(loss_val) if isinstance(loss_val, str) else loss_val
        account_risk_pct = loss_dec / account_balance_usd

        risk_band = self._risk_band(account_risk_pct)
        lev_cat = self._lev_category(leverage)
        quality = self._quality(leverage, account_risk_pct, liq_dist)

        return {
            "asset": asset,
            "position_size_usd": str(position_size_usd),
            "leverage": str(leverage),
            "account_balance_usd": str(account_balance_usd),
            "margin_required_usd": str(margin_required),
            "liq_distance_pct": str(liq_dist),
            "scenarios": scenarios,
            "risk_band": risk_band,
            "leverage_category": lev_cat,
            "quality": quality,
        }

    def suggest_sizes(
        self, account_balance_usd: Decimal, leverage: Decimal
    ) -> dict[str, str]:
        # Based on an illustrative 2% adverse move assumption
        def _suggest(risk_pct):
            max_loss = account_balance_usd * risk_pct
            size = max_loss / Decimal("0.02")
            return size.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        return {
            "conservative": str(_suggest(self.education.conservative_account_risk)),
            "moderate": str(_suggest(self.education.moderate_account_risk)),
            "aggressive": str(_suggest(self.education.aggressive_account_risk)),
        }

    def _scenarios(
        self, size: Decimal, balance: Decimal
    ) -> dict[str, dict[str, Decimal]]:
        out = {}
        for name, move in [
            ("small_0_5pct", Decimal("0.005")),
            ("moderate_1pct", Decimal("0.01")),
            ("stress_2pct", Decimal("0.02")),
            ("crash_5pct", Decimal("0.05")),
            ("black_swan_10pct", Decimal("0.10")),
        ]:
            loss = size * move
            impact = (loss / balance) if balance > 0 else Decimal("0")
            out[name] = {
                "move_pct": move,
                "loss_usd": loss,
                "account_impact_pct": impact,
            }
        return out

    def _risk_band(self, account_risk_pct: Decimal) -> str:
        e = self.education
        if account_risk_pct >= e.aggressive_account_risk:
            return "extreme"
        elif account_risk_pct >= e.moderate_account_risk:
            return "aggressive"
        elif account_risk_pct >= e.conservative_account_risk:
            return "moderate"
        return "conservative"

    def _lev_category(self, lev: Decimal) -> str:
        if lev >= self.education.extreme_lev_warn:
            return "Ultra-High (200x+)"
        if lev >= self.education.high_lev_warn:
            return "Very High (50x–199x)"
        if lev >= Decimal("10"):
            return "Moderate (10x–49x)"
        return "Conservative (<10x)"

    def _quality(
        self, lev: Decimal, acct_risk: Decimal, liq_dist: Decimal
    ) -> dict[str, str]:
        score = 100
        if lev > Decimal("100"):
            score -= 30
        elif lev > Decimal("50"):
            score -= 15
        elif lev > Decimal("25"):
            score -= 5

        if acct_risk > Decimal("0.10"):
            score -= 25
        elif acct_risk > Decimal("0.05"):
            score -= 10

        if liq_dist < Decimal("0.01"):
            score -= 20
        elif liq_dist < Decimal("0.02"):
            score -= 10

        if score >= 80:
            rating, desc = "Excellent", "Conservative profile with good safety margins"
        elif score >= 60:
            rating, desc = "Good", "Moderate risk with reasonable margins"
        elif score >= 40:
            rating, desc = "Risky", "High risk; close monitoring suggested"
        else:
            rating, desc = "Very Risky", "Extreme risk; minimal safety margins"

        return {"score": str(max(0, score)), "rating": rating, "description": desc}


# Global instance
calculator = RiskCalculator()
