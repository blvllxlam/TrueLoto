from dataclasses import dataclass
from datetime import datetime

from aiogram.types import User as TelegramUser

from bot.api import post
from bot.settings import get_admin_telegram_id


@dataclass
class User:
    id: int
    telegram_id: int
    username: str | None
    first_name: str
    created_at: datetime
    is_admin: bool
    language_code: str | None
    participation_status: str
    participation_amount: float
    winning_chance: float
    wins_count: int
    losses_count: int
    payment_status: str


def _to_user(data: dict | None) -> User | None:
    if not data:
        return None
    created_at = data.get("created_at")
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        created = datetime.utcnow()
    return User(
        id=int(data["id"]), telegram_id=int(data["telegram_id"]),
        username=data.get("username"), first_name=data.get("first_name") or "Telegram user",
        created_at=created, is_admin=bool(data.get("is_admin")),
        language_code=data.get("language_code"),
        participation_status=data.get("participation_status") or "not_participating",
        participation_amount=float(data.get("participation_amount") or 0),
        winning_chance=float(data.get("winning_chance") or 0),
        wins_count=int(data.get("wins_count") or 0), losses_count=int(data.get("losses_count") or 0),
        payment_status=data.get("payment_status") or "not_paid",
    )


def get_or_create_user(telegram_user: TelegramUser) -> tuple[User, bool]:
    previous = get_user(telegram_user.id)
    result = post("/internal/users/upsert", {
        "telegram_id": str(telegram_user.id), "username": telegram_user.username,
        "first_name": telegram_user.first_name or "Telegram user",
        "language_code": telegram_user.language_code,
        "is_admin": telegram_user.id == get_admin_telegram_id(),
    })
    user = _to_user(result.get("user"))
    if user is None:
        raise RuntimeError("Worker API не вернул профиль пользователя.")
    return user, previous is None


def get_user(telegram_id: int) -> User | None:
    result = post("/internal/users/get", {"telegram_id": str(telegram_id)})
    return _to_user(result.get("user"))


def set_user_language(telegram_id: int, language_code: str) -> None:
    post("/internal/users/update", {"telegram_id": str(telegram_id), "field": "language_code", "value": language_code})


def set_participation_status(telegram_id: int, status: str) -> None:
    post("/internal/users/update", {"telegram_id": str(telegram_id), "field": "participation_status", "value": status})


def set_payment_status(telegram_id: int, status: str) -> None:
    post("/internal/users/update", {"telegram_id": str(telegram_id), "field": "payment_status", "value": status})
