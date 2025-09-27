from __future__ import annotations
from typing import Iterable, List, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def chunk_buttons(buttons: Iterable[InlineKeyboardButton], n: int = 3) -> List[List[InlineKeyboardButton]]:
    buttons = list(buttons)
    return [buttons[i : i + n] for i in range(0, len(buttons), n)]


def kb(rows: List[List[Tuple[str, str]]]) -> InlineKeyboardMarkup:
    """
    rows: [[(text, callback_data), ...], ...]
    """
    built = [
        [InlineKeyboardButton(text, callback_data=data) for (text, data) in row]
        for row in rows
    ]
    return InlineKeyboardMarkup(built)
