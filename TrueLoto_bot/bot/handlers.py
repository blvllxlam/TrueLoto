from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import (
    main_keyboard,
    participation_keyboard,
    test_deposit_keyboard,
    test_payment_keyboard,
)
from bot.services.draws import get_draw_settings
from bot.services.users import (
    get_or_create_user,
    get_user,
    set_participation_status,
    set_payment_status,
    set_user_language,
)
from bot.settings import get_draw_datetime
from bot.texts import LANGUAGE_NAMES, TEXTS, language_keyboard, text_for


router = Router()


def get_message_language(message: Message) -> str | None:
    """Определяет сохранённый язык отправителя сообщения."""
    if message.from_user is None:
        return None

    user = get_user(message.from_user.id)
    return user.language_code if user is not None else None


def can_participate(status: str) -> bool:
    """Определяет, доступен ли пользователю новый вход в розыгрыш."""
    return status not in {"waiting_draw", "declined_for_karma"}


def format_winning_chance(chance: float) -> str:
    """Преобразует вероятность из БД в проценты для интерфейса."""
    return f"{float(chance) * 100:.2f}%"


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    """Регистрирует пользователя и показывает язык либо главное меню."""
    if message.from_user is None:
        return

    user, _ = get_or_create_user(message.from_user)

    if user.language_code is None:
        await message.answer(
            f"{text_for('ru')['test_notice']}\n\nВыберите язык / Choose a language:",
            reply_markup=language_keyboard(),
        )
        return

    texts = text_for(user.language_code)
    await message.answer(
        f"{texts['test_notice']}\n\n{texts['menu']}",
        reply_markup=main_keyboard(user.language_code, can_participate(user.participation_status)),
    )


@router.message(lambda message: message.text in LANGUAGE_NAMES.values())
async def choose_language(message: Message) -> None:
    """Сохраняет язык и открывает главное меню."""
    if message.from_user is None:
        return

    language_code = next(
        code for code, language_name in LANGUAGE_NAMES.items() if language_name == message.text
    )
    set_user_language(message.from_user.id, language_code)
    texts = text_for(language_code)
    await message.answer(texts["language_selected"])
    user = get_user(message.from_user.id)
    await message.answer(
        f"{texts['test_notice']}\n\n{texts['menu']}",
        reply_markup=main_keyboard(
            language_code, can_participate(user.participation_status) if user else True
        ),
    )


@router.message(lambda message: message.text in {value["participate"] for value in TEXTS.values()})
async def participate(message: Message) -> None:
    """Открывает тестовый сценарий участия."""
    language_code = get_message_language(message)
    texts = text_for(language_code)
    await message.answer(
        texts["choose_participation"], reply_markup=participation_keyboard(language_code)
    )


@router.message(
    lambda message: message.text in {value["join_draw"] for value in TEXTS.values()}
    or message.text in {value["decline_prize"] for value in TEXTS.values()}
)
async def choose_participation(message: Message) -> None:
    """Обрабатывает шаги тестового участия без реальных платежей."""
    if message.from_user is None:
        return

    user = get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте /start.")
        return

    action = (
        "draw"
        if message.text in {value["join_draw"] for value in TEXTS.values()}
        else "decline"
    )
    texts = text_for(user.language_code)
    set_participation_status(user.telegram_id, f"pending_deposit_{action}")
    set_payment_status(user.telegram_id, "not_paid")
    await message.answer(
        texts["deposit_step"], reply_markup=test_deposit_keyboard(user.language_code)
    )


@router.message(lambda message: message.text in {value["test_deposit"] for value in TEXTS.values()})
async def make_test_deposit(message: Message) -> None:
    if message.from_user is None:
        return
    user = get_user(message.from_user.id)
    if user is None or user.participation_status not in {
        "pending_deposit_draw", "pending_deposit_decline"
    }:
        await message.answer("Начните сценарий через кнопку участия.")
        return

    choice = user.participation_status.removeprefix("pending_deposit_")
    set_participation_status(user.telegram_id, f"pending_confirmation_{choice}")
    set_payment_status(user.telegram_id, "test_deposit")
    texts = text_for(user.language_code)
    await message.answer(
        texts["payment_step"], reply_markup=test_payment_keyboard(user.language_code)
    )


@router.message(
    lambda message: message.text in {value["confirm_test_payment"] for value in TEXTS.values()}
)
async def confirm_test_payment(message: Message) -> None:
    if message.from_user is None:
        return
    user = get_user(message.from_user.id)
    if user is None:
        return

    texts = text_for(user.language_code)
    if user.participation_status == "pending_confirmation_draw":
        set_participation_status(user.telegram_id, "waiting_draw")
        set_payment_status(user.telegram_id, "test_paid")
        settings = get_draw_settings()
        draw_datetime = (
            settings.draw_datetime.strftime("%d.%m.%Y %H:%M")
            if settings.draw_datetime
            else get_draw_datetime()
        )
        await message.answer(
            texts["waiting_draw"].format(draw_datetime=draw_datetime),
            reply_markup=main_keyboard(user.language_code, can_participate=False),
        )
    elif user.participation_status == "pending_confirmation_decline":
        set_participation_status(user.telegram_id, "declined_for_karma")
        set_payment_status(user.telegram_id, "test_paid")
        await message.answer(
            texts["decline_complete"], reply_markup=main_keyboard(user.language_code, can_participate=False)
        )
    else:
        await message.answer("Начните сценарий через кнопку участия.")


@router.message(lambda message: message.text in {value["status"] for value in TEXTS.values()})
async def user_status(message: Message) -> None:
    """Показывает данные зарегистрированного пользователя."""
    if message.from_user is None:
        return

    user = get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте команду /start.")
        return

    texts = text_for(user.language_code)
    status = (
        texts["not_participating"]
        if user.participation_status in {"not_participating", "Не участвуете"}
        else texts["status_waiting_draw"]
        if user.participation_status == "waiting_draw"
        else texts["status_declined"]
        if user.participation_status == "declined_for_karma"
        else user.participation_status
    )
    registration_date = user.created_at.strftime("%d.%m.%Y %H:%M")
    await message.answer(
        f"{texts['name']}: {user.first_name}\n"
        f"{texts['registration_date']}: {registration_date}\n"
        f"{texts['participation_status']}: "
        f"{status}\n"
        f"{texts['winning_chance']}: {format_winning_chance(user.winning_chance)}"
    )


@router.message(lambda message: message.text in {value["rules"] for value in TEXTS.values()})
async def rules(message: Message) -> None:
    """Отправляет временный текст правил."""
    await message.answer(text_for(get_message_language(message))["rules_text"])


@router.message(
    lambda message: message.text in {value["language_selection"] for value in TEXTS.values()}
)
async def language_selection(message: Message) -> None:
    """Повторно открывает выбор языка."""
    await message.answer(
        "Выберите язык / Choose a language:",
        reply_markup=language_keyboard(get_message_language(message)),
    )


@router.message(lambda message: message.text in {value["back"] for value in TEXTS.values()})
async def go_back(message: Message) -> None:
    """Возвращает пользователя на предыдущий доступный экран."""
    if message.from_user is None:
        return
    user = get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте /start.")
        return

    texts = text_for(user.language_code)
    if user.participation_status.startswith("pending_confirmation_"):
        choice = user.participation_status.removeprefix("pending_confirmation_")
        set_participation_status(user.telegram_id, f"pending_deposit_{choice}")
        set_payment_status(user.telegram_id, "not_paid")
        await message.answer(
            texts["deposit_step"], reply_markup=test_deposit_keyboard(user.language_code)
        )
    elif user.participation_status.startswith("pending_deposit_"):
        await message.answer(
            texts["choose_participation"], reply_markup=participation_keyboard(user.language_code)
        )
    else:
        await message.answer(
            texts["menu"],
            reply_markup=main_keyboard(user.language_code, can_participate(user.participation_status)),
        )
