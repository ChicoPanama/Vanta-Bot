"""
Tests for Risk Calculator Service
"""
import pytest
from decimal import Decimal
from src.services.risk_calculator import risk_calculator, RiskCalculator, RiskEducationCfg


@pytest.mark.asyncio
async def test_analyze_basic():
    """Test basic risk analysis functionality"""
    result = await risk_calculator.analyze(
        position_size_usd=Decimal("1000"),
        leverage=Decimal("20"),
        account_balance_usd=Decimal("10000"),
        asset="ETH"
    )
    
    assert result["can_execute"] is True
    assert "scenarios" in result
    assert "position_quality" in result
    assert "educational_warnings" in result
    assert result["asset"] == "ETH"
    assert result["leverage_category"] == "Moderate (10-49x)"


@pytest.mark.asyncio
async def test_analyze_high_leverage():
    """Test analysis with high leverage"""
    result = await risk_calculator.analyze(
        position_size_usd=Decimal("5000"),
        leverage=Decimal("100"),
        account_balance_usd=Decimal("10000"),
        asset="BTC"
    )
    
    assert result["can_execute"] is True
    assert result["leverage_category"] == "Very High (100-199x)"
    assert result["liq_distance_pct"] == Decimal("0.01")  # 1/100
    assert len(result["educational_warnings"]) > 0


@pytest.mark.asyncio
async def test_analyze_extreme_risk():
    """Test analysis with extreme risk scenario"""
    result = await risk_calculator.analyze(
        position_size_usd=Decimal("8000"),
        leverage=Decimal("50"),
        account_balance_usd=Decimal("10000"),
        asset="SOL"
    )
    
    assert result["can_execute"] is True
    assert result["risk_level"] in ["aggressive", "extreme"]
    assert result["account_risk_pct"] > Decimal("0.05")  # > 5%


@pytest.mark.asyncio
async def test_insufficient_balance():
    """Test error handling for insufficient balance"""
    with pytest.raises(ValueError, match="Insufficient balance"):
        await risk_calculator.analyze(
            position_size_usd=Decimal("10000"),
            leverage=Decimal("10"),
            account_balance_usd=Decimal("1000"),  # Not enough margin
            asset="ETH"
        )


@pytest.mark.asyncio
async def test_invalid_inputs():
    """Test error handling for invalid inputs"""
    with pytest.raises(ValueError, match="must be positive"):
        await risk_calculator.analyze(
            position_size_usd=Decimal("-1000"),  # Negative
            leverage=Decimal("20"),
            account_balance_usd=Decimal("10000"),
            asset="ETH"
        )


def test_risk_education_cfg():
    """Test risk education configuration"""
    cfg = RiskEducationCfg()
    assert cfg.conservative_account_risk == Decimal("0.02")
    assert cfg.moderate_account_risk == Decimal("0.05")
    assert cfg.aggressive_account_risk == Decimal("0.10")
    assert cfg.warn_leverage_high == Decimal("50")
    assert cfg.warn_leverage_extreme == Decimal("200")


def test_leverage_categorization():
    """Test leverage categorization logic"""
    calc = RiskCalculator()
    
    assert calc._lev_cat(Decimal("5")) == "Conservative (<10x)"
    assert calc._lev_cat(Decimal("25")) == "Moderate (10-49x)"
    assert calc._lev_cat(Decimal("75")) == "High (50-99x)"
    assert calc._lev_cat(Decimal("150")) == "Very High (100-199x)"
    assert calc._lev_cat(Decimal("300")) == "Ultra-High (200x+)"


def test_risk_level_calculation():
    """Test risk level calculation"""
    cfg = RiskEducationCfg()
    calc = RiskCalculator(cfg)
    
    assert calc._level(Decimal("0.01")) == calc._level.__self__.RiskLevel.CONSERVATIVE
    assert calc._level(Decimal("0.03")) == calc._level.__self__.RiskLevel.MODERATE
    assert calc._level(Decimal("0.07")) == calc._level.__self__.RiskLevel.AGGRESSIVE
    assert calc._level(Decimal("0.15")) == calc._level.__self__.RiskLevel.EXTREME


def test_scenario_calculation():
    """Test scenario calculation"""
    calc = RiskCalculator()
    scenarios = calc._scenarios(Decimal("1000"), Decimal("10000"))
    
    assert "move_0_5" in scenarios
    assert "move_1_0" in scenarios
    assert "stress_move" in scenarios
    assert "crash_5" in scenarios
    assert "black_swan_10" in scenarios
    
    # Test that losses increase with move size
    assert scenarios["move_0_5"]["loss"] < scenarios["move_1_0"]["loss"]
    assert scenarios["move_1_0"]["loss"] < scenarios["stress_move"]["loss"]
    assert scenarios["stress_move"]["loss"] < scenarios["crash_5"]["loss"]


def test_position_quality_scoring():
    """Test position quality scoring"""
    calc = RiskCalculator()
    
    # Conservative position should score high
    quality_cons = calc._quality(Decimal("10"), Decimal("0.02"), Decimal("0.05"))
    assert quality_cons["score"] >= 80
    
    # Risky position should score lower
    quality_risk = calc._quality(Decimal("100"), Decimal("0.15"), Decimal("0.005"))
    assert quality_risk["score"] < 60


@pytest.mark.asyncio
async def test_warnings_generation():
    """Test warning generation logic"""
    result = await risk_calculator.analyze(
        position_size_usd=Decimal("5000"),
        leverage=Decimal("250"),  # Extreme leverage
        account_balance_usd=Decimal("10000"),
        asset="ETH"
    )
    
    warnings = result["educational_warnings"]
    assert len(warnings) > 0
    
    # Should have extreme leverage warning
    extreme_warning = next((w for w in warnings if w["type"] == "lev_extreme"), None)
    assert extreme_warning is not None
    assert extreme_warning["severity"] == "high"
