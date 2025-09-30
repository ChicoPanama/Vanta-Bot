"""Telegram inline keyboards (Phase 5)."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def side_kb() -> InlineKeyboardMarkup:
    """Side selection keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Long 📈", "side:LONG"),
                InlineKeyboardButton("Short 📉", "side:SHORT"),
            ]
        ]
    )


def lev_kb() -> InlineKeyboardMarkup:
    """Leverage selection keyboard."""
    rows = [(2, 3, 5), (7, 10, 15)]
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"{x}x", f"lev:{x}") for x in row] for row in rows]
    )


def slip_kb() -> InlineKeyboardMarkup:
    """Slippage selection keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("0.2%", "slip:0.2"),
                InlineKeyboardButton("0.5%", "slip:0.5"),
                InlineKeyboardButton("1.0%", "slip:1.0"),
            ]
        ]
    )


def confirm_kb(tag: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Confirm ✅", f"confirm:{tag}"),
                InlineKeyboardButton("Cancel ❌", "cancel"),
            ]
        ]
    )
