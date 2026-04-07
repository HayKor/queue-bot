from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_join_keyboard(queue_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✋ Занять очередь", callback_data=f"join_{queue_id}")
    return builder.as_markup()
