from __future__ import annotations

from collections.abc import Iterable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def chunk_buttons(
    buttons: Iterable[InlineKeyboardButton], n: int = 3
) -> list[list[InlineKeyboardButton]]:
    buttons = list(buttons)
    return [buttons[i : i + n] for i in range(0, len(buttons), n)]


def kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    """
    rows: [[(text, callback_data), ...], ...]
    """
    built = [
        [InlineKeyboardButton(text, callback_data=data) for (text, data) in row]
        for row in rows
    ]
    return InlineKeyboardMarkup(built)
