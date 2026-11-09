import os

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from bot.texts import text_for


def main_keyboard(language_code: str | None, can_participate: bool = True) -> ReplyKeyboardMarkup:
    """Создаёт главное меню с кнопкой запуска Telegram Mini App."""
    texts = text_for(language_code)
    mini_app_url = os.getenv(
        "MINI_APP_URL",
        "https://mini-app.trueloto-mini-app.pages.dev",
    )
    keyboard = [
        [KeyboardButton(
            text=texts["open_app"],
            web_app=WebAppInfo(url=mini_app_url),
        )],
        [KeyboardButton(text=texts["status"])],
        [KeyboardButton(text=texts["rules"])],
        [KeyboardButton(text=texts["language_selection"])],
        [KeyboardButton(text=texts["back"])],
    ]
    if can_participate:
        keyboard.insert(1, [KeyboardButton(text=texts["participate"])])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


def participation_keyboard(language_code: str | None) -> ReplyKeyboardMarkup:
    """Создаёт тестовое меню участия в розыгрыше."""
    texts = text_for(language_code)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts["join_draw"])],
            [KeyboardButton(text=texts["decline_prize"])],
            [KeyboardButton(text=texts["back"])],
        ],
        resize_keyboard=True,
    )
