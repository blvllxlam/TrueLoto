from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from bot.texts import text_for


MINI_APP_URL = "https://snowy-union-1f23.b-lvl-lxl-am-a7b.workers.dev/"


def main_keyboard(language_code: str | None, can_participate: bool = True) -> ReplyKeyboardMarkup:
    """Создаёт главное меню на выбранном языке."""
    texts = text_for(language_code)
    keyboard = [
        [KeyboardButton(text="🎟 TrueLoto Mini App", web_app=WebAppInfo(url=MINI_APP_URL))],
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


def test_deposit_keyboard(language_code: str | None) -> ReplyKeyboardMarkup:
    texts = text_for(language_code)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts["test_deposit"])],
            [KeyboardButton(text=texts["back"])],
        ],
        resize_keyboard=True,
    )


def test_payment_keyboard(language_code: str | None) -> ReplyKeyboardMarkup:
    texts = text_for(language_code)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts["confirm_test_payment"])],
            [KeyboardButton(text=texts["back"])],
        ],
        resize_keyboard=True,
    )
