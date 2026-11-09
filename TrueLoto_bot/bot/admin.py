from datetime import datetime

from aiogram import Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from bot.services.draws import (
    get_draw_settings,
    get_users,
    get_waiting_draw_count,
    run_test_draw,
    update_draw_datetime,
    update_participant_limit,
)
from bot.services.users import get_user
from bot.keyboards import main_keyboard
from bot.texts import text_for


router = Router()


class DrawSetup(StatesGroup):
    waiting_datetime = State()
    waiting_participant_limit = State()


ADMIN_BUTTONS = {
    "users": "Участники",
    "settings": "Настройки розыгрыша",
    "datetime": "Установить дату и время",
    "limit": "Установить лимит участников",
    "start": "Запустить тестовый розыгрыш",
}


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            *[[KeyboardButton(text=button)] for button in ADMIN_BUTTONS.values()],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def is_admin(telegram_id: int) -> bool:
    user = get_user(telegram_id)
    return user is not None and user.is_admin


def participant_status_label(status: str) -> str:
    labels = {
        "not_participating": "Не участвует",
        "waiting_draw": "Ожидает розыгрыш",
        "declined_for_karma": "Отказался от выигрыша",
        "pending_deposit_draw": "Ожидает депозит для участия",
        "pending_deposit_decline": "Ожидает депозит после отказа",
        "pending_confirmation_draw": "Ожидает подтверждение оплаты",
        "pending_confirmation_decline": "Ожидает подтверждение оплаты",
    }
    return labels.get(status, status)


def payment_status_label(status: str) -> str:
    labels = {
        "not_paid": "Не оплачено",
        "test_deposit": "Депозит внесён (тест)",
        "test_paid": "Оплата подтверждена (тест)",
    }
    return labels.get(status, status)


def format_winning_chance(chance: float) -> str:
    return f"{float(chance) * 100:.2f}%"


@router.message(Command("myid"))
async def my_id(message: Message) -> None:
    """Показывает пользователю его Telegram ID для настройки администратора."""
    if message.from_user is not None:
        await message.answer(f"Ваш Telegram ID: {message.from_user.id}")


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return

    await message.answer("Админ-панель TrueLoto", reply_markup=admin_keyboard())


@router.message(lambda message: message.text in ADMIN_BUTTONS.values())
async def admin_actions(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    action = next(key for key, button in ADMIN_BUTTONS.items() if button == message.text)
    if action == "users":
        users = get_users()
        if not users:
            await message.answer("Зарегистрированных участников пока нет.")
        else:
            lines = [f"Всего зарегистрировано: {len(users)}", ""]
            for user in users:
                username = f"@{user.username}" if user.username else "без username"
                lines.append(
                    f"ID: {user.telegram_id} | {user.first_name} ({username})\n"
                    f"Оплата: {payment_status_label(user.payment_status)}\n"
                    f"Участие: {participant_status_label(user.participation_status)}\n"
                    f"Шанс на победу: {format_winning_chance(user.winning_chance)}"
                )
            await message.answer("\n\n".join(lines))
    elif action == "settings":
        settings = get_draw_settings()
        draw_datetime = (
            settings.draw_datetime.strftime("%d.%m.%Y %H:%M")
            if settings.draw_datetime
            else "не установлены"
        )
        limit = settings.participant_limit or "не установлен"
        await message.answer(
            f"Дата и время: {draw_datetime}\n"
            f"Лимит участников: {limit}\n"
            f"Участников ожидает розыгрыш: {get_waiting_draw_count()}\n"
            f"Статус: {settings.status}"
        )
    elif action == "datetime":
        await state.set_state(DrawSetup.waiting_datetime)
        await message.answer(
            "Отправьте дату и время в формате: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 31.12.2026 20:00"
        )
    elif action == "limit":
        await state.set_state(DrawSetup.waiting_participant_limit)
        await message.answer("Отправьте нужное количество участников целым числом.")
    elif action == "start":
        settings = get_draw_settings()
        waiting_count = get_waiting_draw_count()
        if settings.draw_datetime is None or settings.participant_limit is None:
            await message.answer("Сначала установите дату и лимит участников.")
        elif waiting_count != settings.participant_limit:
            await message.answer(
                f"Нужно ровно {settings.participant_limit} участников. Сейчас: {waiting_count}."
            )
        else:
            result = run_test_draw()
            for participant in result.participants:
                texts = text_for(participant.language_code)
                result_text = (
                    texts["draw_winner"]
                    if participant.telegram_id == result.winner_telegram_id
                    else texts["draw_not_winner"]
                )
                try:
                    await message.bot.send_message(
                        participant.telegram_id,
                        result_text,
                        reply_markup=main_keyboard(participant.language_code, True),
                    )
                except TelegramForbiddenError:
                    continue
            await message.answer(
                f"Тестовый розыгрыш завершён. Победитель: {result.winner_telegram_id}. "
                f"Суммарный вес: {result.total_weight}."
            )


@router.message(DrawSetup.waiting_datetime)
async def save_datetime(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        draw_datetime = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except (AttributeError, ValueError):
        await message.answer("Неверный формат. Пример: 31.12.2026 20:00")
        return

    update_draw_datetime(draw_datetime)
    await state.clear()
    await message.answer("Дата и время розыгрыша сохранены.", reply_markup=admin_keyboard())


@router.message(DrawSetup.waiting_participant_limit)
async def save_participant_limit(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        participant_limit = int(message.text.strip())
        if participant_limit < 1:
            raise ValueError
    except (AttributeError, ValueError):
        await message.answer("Введите целое положительное число.")
        return

    update_participant_limit(participant_limit)
    await state.clear()
    await message.answer("Лимит участников сохранён.", reply_markup=admin_keyboard())


@router.message(lambda message: message.text == "⬅️ Назад")
async def leave_admin_panel(message: Message, state: FSMContext) -> None:
    """Закрывает админ-панель и возвращает обычное меню."""
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    await state.clear()
    user = get_user(message.from_user.id)
    if user is not None:
        texts = text_for(user.language_code)
        can_participate = user.participation_status not in {
            "waiting_draw", "declined_for_karma"
        }
        await message.answer(
            texts["menu"],
            reply_markup=main_keyboard(user.language_code, can_participate),
        )
