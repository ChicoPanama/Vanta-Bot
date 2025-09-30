"""
Unit tests for alerts functionality
"""

# Import the alerts module
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.copytrading.alerts import (
    _recent_notifications,
    fanout_trader_signal,
    on_trader_signal,
    send_daily_digest,
)


@pytest.fixture
def mock_bot():
    """Mock Telegram bot"""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_copy_service():
    """Mock copy service"""
    with patch("src.services.copytrading.alerts.copy_service") as mock:
        mock.get_cfg.return_value = {
            "auto_copy": True,
            "notify": True,
            "sizing_mode": "MIRROR",
        }
        mock.maybe_autocopy_on_signal = AsyncMock(return_value=(True, "copied"))
        mock.list_follows.return_value = []
        yield mock


@pytest.fixture
def mock_users_by_trader():
    """Mock users_by_trader function"""
    with patch("src.services.copytrading.alerts.users_by_trader") as mock:
        mock.return_value = [12345, 67890]
        yield mock


@pytest.fixture
def clear_notifications():
    """Clear notification dedupe cache before each test"""
    _recent_notifications.clear()
    yield
    _recent_notifications.clear()


@pytest.mark.asyncio
async def test_send_daily_digest_no_follows(mock_bot, mock_copy_service):
    """Test daily digest when user has no follows"""
    mock_copy_service.list_follows.return_value = []

    await send_daily_digest(mock_bot, 12345)

    # Should not send any message
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_daily_digest_with_follows(mock_bot, mock_copy_service):
    """Test daily digest with follows"""
    mock_copy_service.list_follows.return_value = [
        ("trader1", {"auto_copy": True, "notify": True}),
        ("trader2", {"auto_copy": False, "notify": True}),
    ]

    await send_daily_digest(mock_bot, 12345)

    # Should send digest message
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert call_args[1]["chat_id"] == 12345
    assert call_args[1]["parse_mode"] == "Markdown"

    # Check message content
    message = call_args[1]["text"]
    assert "*Daily Digest*" in message
    assert "trader1" in message
    assert "trader2" in message
    assert "Auto: ON" in message
    assert "Auto: OFF" in message


@pytest.mark.asyncio
async def test_fanout_trader_signal(mock_bot, mock_users_by_trader, mock_copy_service):
    """Test fanout signal to multiple users"""
    signal = {
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 10,
        "notional_usd": 500,
        "collateral_usdc": 50,
    }

    await fanout_trader_signal(mock_bot, "test_trader", signal)

    # Should call on_trader_signal for each user
    assert mock_copy_service.maybe_autocopy_on_signal.call_count == 2

    # Check that both users were processed
    calls = mock_copy_service.maybe_autocopy_on_signal.call_args_list
    user_ids = [call[0][0] for call in calls]
    assert set(user_ids) == {12345, 67890}


@pytest.mark.asyncio
async def test_on_trader_signal_with_notification(
    mock_bot, mock_copy_service, clear_notifications
):
    """Test signal processing with notification enabled"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
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

    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Should send notification
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert call_args[1]["chat_id"] == 12345
    assert call_args[1]["parse_mode"] == "Markdown"

    # Check notification content
    message = call_args[1]["text"]
    assert "*Followed Trader*" in message
    assert "test_trader" in message
    assert "ETH/USD LONG" in message
    assert "lev:10" in message
    assert "notional:$500" in message


@pytest.mark.asyncio
async def test_on_trader_signal_notification_disabled(mock_bot, mock_copy_service):
    """Test signal processing with notification disabled"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
        "notify": False,
        "sizing_mode": "MIRROR",
    }

    signal = {
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 10,
        "notional_usd": 500,
        "collateral_usdc": 50,
    }

    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Should not send notification
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_on_trader_signal_server_dry_notification(
    mock_bot, mock_copy_service, clear_notifications
):
    """Test server dry mode notification"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
    }
    mock_copy_service.maybe_autocopy_on_signal.return_value = (False, "server_dry")

    signal = {
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 10,
        "notional_usd": 500,
        "collateral_usdc": 50,
    }

    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Should send both trade notification and server dry notification
    assert mock_bot.send_message.call_count == 2

    # Check server dry notification
    calls = mock_bot.send_message.call_args_list
    server_dry_message = calls[1][1]["text"]
    assert "Auto-copy is ON but server is in DRY mode" in server_dry_message


@pytest.mark.asyncio
async def test_on_trader_signal_executor_missing_notification(
    mock_bot, mock_copy_service, clear_notifications
):
    """Test executor missing notification"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
    }
    mock_copy_service.maybe_autocopy_on_signal.return_value = (
        False,
        "executor_missing",
    )

    signal = {
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 10,
        "notional_usd": 500,
        "collateral_usdc": 50,
    }

    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Should send both trade notification and executor missing notification
    assert mock_bot.send_message.call_count == 2

    # Check executor missing notification
    calls = mock_bot.send_message.call_args_list
    executor_message = calls[1][1]["text"]
    assert "executor is not installed" in executor_message


@pytest.mark.asyncio
async def test_notification_dedupe(mock_bot, mock_copy_service, clear_notifications):
    """Test notification deduplication"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
    }
    mock_copy_service.maybe_autocopy_on_signal.return_value = (False, "server_dry")

    signal = {
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 10,
        "notional_usd": 500,
        "collateral_usdc": 50,
    }

    # Send first signal
    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Send second signal immediately (should be deduplicated)
    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Should only send 3 messages total (2 trade notifications + 1 server dry notification)
    # The second server dry notification should be deduplicated
    assert mock_bot.send_message.call_count == 3


@pytest.mark.asyncio
async def test_notification_dedupe_expires(
    mock_bot, mock_copy_service, clear_notifications
):
    """Test notification deduplication expires after TTL"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
    }
    mock_copy_service.maybe_autocopy_on_signal.return_value = (False, "server_dry")

    signal = {
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 10,
        "notional_usd": 500,
        "collateral_usdc": 50,
    }

    # Send first signal
    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Manually expire the dedupe cache (simulate 5+ minutes passing)
    _recent_notifications["12345:server_dry"] = time.time() - 301

    # Send second signal (should not be deduplicated)
    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Should send 4 messages total (2 trade notifications + 2 server dry notifications)
    assert mock_bot.send_message.call_count == 4


@pytest.mark.asyncio
async def test_send_message_error_handling(mock_bot, mock_copy_service):
    """Test error handling when send_message fails"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
    }

    # Mock send_message to raise an exception
    mock_bot.send_message.side_effect = Exception("Telegram API error")

    signal = {
        "pair": "ETH/USD",
        "side": "LONG",
        "lev": 10,
        "notional_usd": 500,
        "collateral_usdc": 50,
    }

    # Should not raise exception
    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Should still attempt auto-copy
    mock_copy_service.maybe_autocopy_on_signal.assert_called_once()


@pytest.mark.asyncio
async def test_fanout_with_many_users(mock_bot, mock_copy_service):
    """Test fanout with many users"""
    # Mock many users following a trader
    with patch("src.services.copytrading.alerts.users_by_trader") as mock_users:
        mock_users.return_value = list(range(100))  # 100 users

        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 500,
            "collateral_usdc": 50,
        }

        await fanout_trader_signal(mock_bot, "popular_trader", signal)

        # Should process all 100 users
        assert mock_copy_service.maybe_autocopy_on_signal.call_count == 100


@pytest.mark.asyncio
async def test_different_failure_reasons(
    mock_bot, mock_copy_service, clear_notifications
):
    """Test different failure reasons don't trigger notifications"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
    }

    test_cases = [
        (False, "auto_copy_off"),
        (False, "over_per_trade_cap"),
        (False, "exec_error"),
    ]

    for ok, reason in test_cases:
        mock_copy_service.maybe_autocopy_on_signal.return_value = (ok, reason)

        signal = {
            "pair": "ETH/USD",
            "side": "LONG",
            "lev": 10,
            "notional_usd": 500,
            "collateral_usdc": 50,
        }

        await on_trader_signal(mock_bot, 12345, "test_trader", signal)

        # Should only send trade notification, no failure notification
        assert mock_bot.send_message.call_count == 1

        mock_bot.reset_mock()
        mock_copy_service.reset_mock()


@pytest.mark.asyncio
async def test_signal_format_validation(mock_bot, mock_copy_service):
    """Test signal format validation and handling"""
    mock_copy_service.get_cfg.return_value = {
        "auto_copy": True,
        "notify": True,
        "sizing_mode": "MIRROR",
    }

    # Test with minimal signal
    signal = {
        "pair": "BTC/USD",
        "side": "SHORT",
        # Missing lev, notional_usd, collateral_usdc
    }

    await on_trader_signal(mock_bot, 12345, "test_trader", signal)

    # Should handle missing fields gracefully
    mock_bot.send_message.assert_called_once()
    mock_copy_service.maybe_autocopy_on_signal.assert_called_once()

    # Check notification content handles missing fields
    call_args = mock_bot.send_message.call_args
    message = call_args[1]["text"]
    assert "BTC/USD SHORT" in message
    assert "lev:" in message  # Should show default or empty
    assert "notional:" in message  # Should show default or empty
