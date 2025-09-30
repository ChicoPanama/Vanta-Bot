from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from telegram import Bot

from src.services.copytrading import copy_service
from src.services.copytrading.copy_store import users_by_trader

log = logging.getLogger(__name__)

# In-memory dedupe for server_dry/executor_missing messages (5min TTL)
_recent_notifications = {}

# Redis dedupe (optional)
_redis_client = None


def _get_redis_client():
    """Get Redis client if available"""
    global _redis_client
    # In tests, prefer in-memory dedupe to avoid external dependencies
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None
    if _redis_client is None:
        try:
            import redis

            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                _redis_client = redis.from_url(redis_url)
                # Test connection
                _redis_client.ping()
            else:
                _redis_client = False  # Mark as unavailable
        except Exception as e:
            log.warning(f"Redis connection failed: {e}")
            _redis_client = False  # Mark as unavailable
    return _redis_client if _redis_client is not False else None


def _is_notification_deduplicated(notification_key: str) -> bool:
    """Check if notification is deduplicated using Redis or in-memory fallback"""
    redis_client = _get_redis_client()

    if redis_client:
        try:
            # Check Redis with TTL
            exists = redis_client.exists(f"copy_alert_dedup:{notification_key}")
            if exists:
                return True

            # Set in Redis with 5min TTL
            redis_client.setex(f"copy_alert_dedup:{notification_key}", 300, "1")
            return False
        except Exception as e:
            # Fall back to in-memory if Redis fails
            log.warning(f"Redis deduplication failed, using in-memory fallback: {e}")
            pass

    # In-memory fallback
    now = time.time()
    if notification_key in _recent_notifications:
        if now - _recent_notifications[notification_key] <= 300:
            return True

    _recent_notifications[notification_key] = now
    return False


async def send_daily_digest(bot: Bot, uid: int):
    follows = copy_service.list_follows(uid)
    if not follows:
        return

    # Keep digest simple and compatible with tests
    lines = ["*Daily Digest*"]
    for tk, cfg in follows:
        auto_state = "ON" if cfg.get("auto_copy") else "OFF"
        notify_state = "ON" if cfg.get("notify") else "OFF"
        lines.append(f"• `{tk}` — Auto: {auto_state} | Notify: {notify_state}")

    try:
        await bot.send_message(
            chat_id=uid, text="\n".join(lines), parse_mode="Markdown"
        )
    except Exception as e:
        log.exception("Failed to send digest to user %s: %s", uid, e)


async def digest_scheduler(bot: Bot, user_ids: list[int], hour_utc: int = 0):
    while True:
        now = time.gmtime()
        if now.tm_hour == hour_utc and now.tm_min < 2:
            for uid in user_ids:
                await send_daily_digest(bot, uid)
            await asyncio.sleep(120)  # avoid duplicate within the same minute
        await asyncio.sleep(30)


async def fanout_trader_signal(bot: Bot, trader_key: str, signal: dict[str, Any]):
    """
    Fan out a trader signal to all users following that trader
    """
    start_time = time.time()
    req_id = signal.get("req_id", f"fanout_{int(start_time * 1000)}")

    following_users = users_by_trader(trader_key)
    log.info(
        "fanout_start",
        extra={
            "trader_key": trader_key,
            "pair": signal.get("pair"),
            "side": signal.get("side"),
            "lev": signal.get("lev"),
            "notional": signal.get("notional_usd"),
            "user_count": len(following_users),
            "req_id": req_id,
        },
    )

    # Batch processing with rate limiting
    sent_count = 0
    for uid in following_users:
        await on_trader_signal(bot, uid, trader_key, signal)
        sent_count += 1

        # Yield control after each send
        await asyncio.sleep(0)

        # Rate limiting: sleep every 20 sends to avoid Telegram 429s
        if sent_count % 20 == 0:
            await asyncio.sleep(0.2)

    # Log fanout completion
    latency_ms = int((time.time() - start_time) * 1000)
    log.info(
        "fanout_complete",
        extra={
            "trader_key": trader_key,
            "pair": signal.get("pair"),
            "side": signal.get("side"),
            "user_count": len(following_users),
            "sent_count": sent_count,
            "req_id": req_id,
            "latency_ms": latency_ms,
        },
    )


async def on_trader_signal(bot: Bot, uid: int, trader_key: str, signal: dict[str, Any]):
    """
    Called by your indexer/tracker when a followed trader opens/closes.
    """
    start_time = time.time()

    # Try to get req_id from signal or generate one
    req_id = signal.get("req_id", f"signal_{int(start_time * 1000)}")

    cfg = copy_service.get_cfg(uid, trader_key)

    # Send notification if enabled
    if cfg.get("notify"):
        side = signal.get("side")
        pair = signal.get("pair")
        lev = signal.get("lev")
        notional = signal.get("notional_usd", 0)
        txt = f"*Followed Trader* `{trader_key}`\n{pair} {side}  lev:{lev}  notional:${notional:,}"

        # Retry logic with exponential backoff
        for attempt in range(3):
            try:
                await bot.send_message(chat_id=uid, text=txt, parse_mode="Markdown")
                break  # Success, exit retry loop
            except Exception as e:
                if attempt == 2:  # Last attempt
                    log.exception(
                        "signal_notify_fail after 3 attempts",
                        extra={
                            "user_id": uid,
                            "trader_key": trader_key,
                            "attempt": attempt + 1,
                            "error": str(e),
                        },
                    )
                else:
                    # Wait before retry (0.5s, 1s)
                    await asyncio.sleep(0.5 * (2**attempt))

    # Attempt auto-copy
    ok, why = await copy_service.maybe_autocopy_on_signal(uid, trader_key, signal)

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    # Log structured decision with enriched fields
    log.info(
        "autocopy_decision",
        extra={
            "user_id": uid,
            "trader_key": trader_key,
            "pair": signal.get("pair"),
            "side": signal.get("side"),
            "lev": signal.get("lev"),
            "notional": signal.get("notional_usd"),
            "reason": why,
            "req_id": req_id,
            "latency_ms": latency_ms,
        },
    )

    # Send one-time info messages for certain failure reasons (with dedupe)
    if not ok and why in ["server_dry", "executor_missing"]:
        notification_key = f"{uid}:{why}"

        # Check if we've sent this notification recently (5min dedupe)
        if not _is_notification_deduplicated(notification_key):
            # Retry logic for notification messages
            for attempt in range(3):
                try:
                    if why == "server_dry":
                        await bot.send_message(
                            chat_id=uid,
                            text="ℹ️ Auto-copy is ON but server is in DRY mode.\nTrades will not be executed until server switches to LIVE mode.",
                        )
                    elif why == "executor_missing":
                        await bot.send_message(
                            chat_id=uid,
                            text="ℹ️ Auto-copy set to ON, but executor is not installed on server.\nTrades are not mirrored yet.",
                        )
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        log.warning(
                            "notification_dedupe_fail",
                            extra={
                                "user_id": uid,
                                "reason": why,
                                "attempt": attempt + 1,
                                "error": str(e),
                            },
                        )
                    else:
                        # Wait before retry (0.5s, 1s)
                        await asyncio.sleep(0.5 * (2**attempt))
