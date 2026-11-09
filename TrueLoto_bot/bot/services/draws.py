from dataclasses import dataclass
from datetime import datetime

from bot.api import get, post
from bot.services.users import User, _to_user


@dataclass
class DrawSettings:
    id: int
    draw_datetime: datetime | None
    participant_limit: int | None
    status: str


@dataclass
class DrawResult:
    winner_telegram_id: int
    participants: list[User]
    total_weight: int


def _to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_draw_settings() -> DrawSettings:
    data = get("/internal/draw/settings").get("settings") or {}
    return DrawSettings(
        id=int(data.get("id", 1)), draw_datetime=_to_datetime(data.get("draw_datetime")),
        participant_limit=data.get("participant_limit"), status=data.get("status") or "not_started",
    )


def update_draw_datetime(draw_datetime: datetime) -> None:
    post("/internal/draw/settings", {"field": "draw_datetime", "value": draw_datetime.isoformat()})


def update_participant_limit(participant_limit: int) -> None:
    post("/internal/draw/settings", {"field": "participant_limit", "value": participant_limit})


def start_test_draw() -> None:
    post("/internal/draw/start", {})


def run_test_draw() -> DrawResult:
    result = post("/internal/draw/run", {})
    participants = [
        User(
            id=0, telegram_id=int(item["telegram_id"]), username=item.get("username"),
            first_name=item.get("first_name") or "Telegram user", created_at=datetime.utcnow(),
            is_admin=False, language_code=item.get("language_code"),
            participation_status="not_participating", participation_amount=0,
            winning_chance=0, wins_count=0, losses_count=0, payment_status="not_paid",
        )
        for item in result.get("participants", [])
    ]
    return DrawResult(int(result["winner_telegram_id"]), participants, int(result["total_weight"]))


def get_users() -> list[User]:
    return [
        user for user in (_to_user(item) for item in get("/internal/users/list").get("users", []))
        if user is not None
    ]


def get_waiting_draw_count() -> int:
    return int(get("/internal/draw/waiting-count").get("count", 0))
