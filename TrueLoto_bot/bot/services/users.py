from aiogram.types import User as TelegramUser
from sqlalchemy import select

from bot.database import SessionLocal
from bot.models import User
from bot.settings import get_admin_telegram_id


def get_or_create_user(telegram_user: TelegramUser) -> tuple[User, bool]:
    """Возвращает пользователя и признак его создания."""
    with SessionLocal() as session:
        user = session.scalar(
            select(User).where(User.telegram_id == telegram_user.id)
        )

        is_admin = telegram_user.id == get_admin_telegram_id()

        if user:
            if user.is_admin != is_admin:
                user.is_admin = is_admin
                session.commit()
            return user, False

        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            is_admin=is_admin,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user, True


def get_user(telegram_id: int) -> User | None:
    """Находит пользователя по Telegram ID."""
    with SessionLocal() as session:
        return session.scalar(select(User).where(User.telegram_id == telegram_id))


def set_user_language(telegram_id: int, language_code: str) -> None:
    """Сохраняет выбранный пользователем язык."""
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is not None:
            user.language_code = language_code
            session.commit()


def set_participation_status(telegram_id: int, status: str) -> None:
    """Сохраняет текущий этап тестового сценария участия."""
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is not None:
            user.participation_status = status
            session.commit()


def set_payment_status(telegram_id: int, status: str) -> None:
    """Сохраняет тестовый статус оплаты."""
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is not None:
            user.payment_status = status
            session.commit()
