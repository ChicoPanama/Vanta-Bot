"""
Unit tests for copy service functionality
"""

# Import the copy service module
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.copytrading.copy_service import (
    get_cfg,
    list_follows,
    maybe_autocopy_on_signal,
    set_cfg,
    unfollow,
)


@pytest.fixture
def mock_copy_store():
    """Mock the copy store for testing"""
    with patch("src.services.copytrading.copy_service.copy_store") as mock:
        # Set up default mock behavior
        mock.get.return_value = {
            "auto_copy": True,
            "notify": True,
            "sizing_mode": "MIRROR",
            "max_leverage": 50,
            "per_trade_cap_usd": 1000.0,
            "daily_cap_usd": 5000.0,
            "use_loss_protection": True,
            "stop_after_losses": 5,
            "stop_after_drawdown_usd": 1000.0,
        }
        mock.put.return_value = None
        mock.remove.return_value = None
        mock.list_follows.return_value = []
        yield mock


@pytest.fixture
def mock_executor():
    """Mock the copy executor"""
    with patch("src.services.copytrading.copy_service.exec_follow") as mock_follow:
        with patch("src.services.copytrading.copy_service.exec_status") as mock_status:
            mock_follow.return_value = {"success": True, "message": "Copied"}
            mock_status.return_value = {"ok": True}
            yield mock_follow, mock_status


@pytest.mark.asyncio
async def test_autocopy_reason_copied(mock_copy_store, mock_executor):
    """Test successful auto-copy"""
    mock_follow, _ = mock_executor

    # Mock server in LIVE mode
    with patch("src.services.copytrading.copy_service.is_live", return_value=True):
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 500,
            "collateral_usdc": 50,
        }

        ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

        assert ok is True
        assert reason == "copied"
        mock_follow.assert_called_once()


@pytest.mark.asyncio
async def test_autocopy_reason_auto_copy_off(mock_copy_store):
    """Test auto-copy when user has it disabled"""
    # Mock user config with auto_copy disabled
    mock_copy_store.get.return_value = {
        "auto_copy": False,
        "notify": True,
        "sizing_mode": "MIRROR",
    }

    signal = {
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 10,
        "notional_usd": 500,
        "collateral_usdc": 50,
    }

    ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

    assert ok is False
    assert reason == "auto_copy_off"


@pytest.mark.asyncio
async def test_autocopy_reason_server_dry(mock_copy_store):
    """Test auto-copy blocked in DRY mode"""
    # Mock server in DRY mode
    with patch("src.services.copytrading.copy_service.is_live", return_value=False):
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 500,
            "collateral_usdc": 50,
        }

        ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

        assert ok is False
        assert reason == "server_dry"


@pytest.mark.asyncio
async def test_autocopy_reason_executor_missing(mock_copy_store):
    """Test auto-copy when executor is not available"""
    # Mock executor not available
    with patch("src.services.copytrading.copy_service.EXECUTOR_OK", False):
        with patch("src.services.copytrading.copy_service.is_live", return_value=True):
            signal = {
                "pair": "ETH/USD",
                "side": "LONG",
                "lev": 10,
                "notional_usd": 500,
                "collateral_usdc": 50,
            }

            ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

            assert ok is False
            assert reason == "executor_missing"


@pytest.mark.asyncio
async def test_autocopy_reason_over_per_trade_cap(mock_copy_store, mock_executor):
    """Test auto-copy blocked by per-trade cap"""
    # Mock user config with low per-trade cap
    mock_copy_store.get.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
        "per_trade_cap_usd": 100.0,  # Low cap
    }

    with patch("src.services.copytrading.copy_service.is_live", return_value=True):
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 1000,  # Exceeds cap
            "collateral_usdc": 100,
        }

        ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

        assert ok is False
        assert reason == "over_per_trade_cap"


@pytest.mark.asyncio
async def test_autocopy_reason_exec_error(mock_copy_store, mock_executor):
    """Test auto-copy when executor throws error"""
    mock_follow, _ = mock_executor
    mock_follow.side_effect = Exception("Executor failed")

    with patch("src.services.copytrading.copy_service.is_live", return_value=True):
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 500,
            "collateral_usdc": 50,
        }

        ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

        assert ok is False
        assert reason == "exec_error"


@pytest.mark.asyncio
async def test_sizing_modes(mock_copy_store, mock_executor):
    """Test different sizing modes"""
    mock_follow, _ = mock_executor

    test_cases = [
        {
            "sizing_mode": "MIRROR",
            "expected_collateral": 50,  # Same as signal
        },
        {
            "sizing_mode": "FIXED_USD",
            "fixed_usd": 200.0,
            "expected_collateral": 20.0,  # 200 / 10 leverage
        },
        {
            "sizing_mode": "PCT_EQUITY",
            "pct_equity": 2.0,
            "expected_collateral": 200.0,  # 10000 * 2% / 10 leverage
        },
    ]

    with patch("src.services.copytrading.copy_service.is_live", return_value=True):
        for case in test_cases:
            mock_copy_store.get.return_value = {
                "auto_copy": True,
                "notify": True,
                "sizing_mode": case["sizing_mode"],
                "fixed_usd": case.get("fixed_usd", 100.0),
                "pct_equity": case.get("pct_equity", 1.0),
                "per_trade_cap_usd": 1000.0,
            }

            signal = {
                "pair": "ETH/USD",
                "side": "LONG",
                "lev": 10,
                "notional_usd": 500,
                "collateral_usdc": 50,
            }

            ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

            assert ok is True
            assert reason == "copied"

            # Check that executor was called with correct collateral
            call_args = mock_follow.call_args
            assert call_args[1]["collateral_usdc"] == case["expected_collateral"]

            mock_follow.reset_mock()


@pytest.mark.asyncio
async def test_slippage_override(mock_copy_store, mock_executor):
    """Test slippage override"""
    mock_follow, _ = mock_executor

    mock_copy_store.get.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
        "slippage_override_pct": 2.0,
    }

    with patch("src.services.copytrading.copy_service.is_live", return_value=True):
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 500,
            "collateral_usdc": 50,
        }

        ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

        assert ok is True
        assert reason == "copied"

        # Check that executor was called with slippage override
        call_args = mock_follow.call_args
        assert call_args[1]["slippage_pct"] == 2.0


def test_service_functions(mock_copy_store):
    """Test basic service functions"""
    # Test get_cfg
    cfg = get_cfg(12345, "test_trader")
    assert cfg["auto_copy"] is True
    mock_copy_store.get.assert_called_with(12345, "test_trader")

    # Test set_cfg
    test_config = {"auto_copy": False}
    set_cfg(12345, "test_trader", test_config)
    mock_copy_store.put.assert_called_with(12345, "test_trader", test_config)

    # Test unfollow
    unfollow(12345, "test_trader")
    mock_copy_store.remove.assert_called_with(12345, "test_trader")

    # Test list_follows
    follows = list_follows(12345)
    assert follows == []
    mock_copy_store.list_follows.assert_called_with(12345)


@pytest.mark.asyncio
async def test_edge_cases(mock_copy_store, mock_executor):
    """Test edge cases and error conditions"""
    mock_follow, _ = mock_executor

    # Test with zero leverage
    mock_copy_store.get.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "FIXED_USD",
        "fixed_usd": 100.0,
        "per_trade_cap_usd": 1000.0,
    }

    with patch("src.services.copytrading.copy_service.is_live", return_value=True):
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 0,  # Zero leverage
            "notional_usd": 100,
            "collateral_usdc": 100,
        }

        ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

        # Should handle zero leverage gracefully
        assert ok is True
        assert reason == "copied"

        # Should use leverage of 1 for calculation
        call_args = mock_follow.call_args
        assert call_args[1]["collateral_usdc"] == 100.0  # 100 / 1


@pytest.mark.asyncio
async def test_missing_signal_fields(mock_copy_store, mock_executor):
    """Test handling of missing signal fields"""
    mock_follow, _ = mock_executor

    with patch("src.services.copytrading.copy_service.is_live", return_value=True):
        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            # Missing lev, notional_usd, collateral_usdc
        }

        ok, reason = await maybe_autocopy_on_signal(12345, "test_trader", signal)

        # Should handle missing fields gracefully
        assert ok is True
        assert reason == "copied"

        call_args = mock_follow.call_args
        assert call_args[1]["leverage"] == 1.0  # Default leverage
        assert call_args[1]["collateral_usdc"] == 0.0  # Default collateral
