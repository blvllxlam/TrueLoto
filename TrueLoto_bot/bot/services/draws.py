from datetime import datetime
from dataclasses import dataclass
from decimal import Decimal
import random

from sqlalchemy import select

from bot.database import SessionLocal
from bot.models import DrawRound, DrawSettings, User


@dataclass
class DrawResult:
    winner_telegram_id: int
    participants: list[User]
    total_weight: int


def get_draw_settings() -> DrawSettings:
    """Возвращает единую запись с настройками розыгрыша."""
    with SessionLocal() as session:
        settings = session.get(DrawSettings, 1)
        if settings is None:
            settings = DrawSettings(id=1)
            session.add(settings)
            session.commit()
        return settings


def update_draw_datetime(draw_datetime: datetime) -> None:
    with SessionLocal() as session:
        settings = session.get(DrawSettings, 1) or DrawSettings(id=1)
        session.add(settings)
        settings.draw_datetime = draw_datetime
        session.commit()


def update_participant_limit(participant_limit: int) -> None:
    with SessionLocal() as session:
        settings = session.get(DrawSettings, 1) or DrawSettings(id=1)
        session.add(settings)
        settings.participant_limit = participant_limit
        session.commit()


def start_test_draw() -> None:
    with SessionLocal() as session:
        settings = session.get(DrawSettings, 1) or DrawSettings(id=1)
        session.add(settings)
        settings.status = "started"
        session.commit()


def run_test_draw() -> DrawResult:
    """Проводит один взвешенный тестовый розыгрыш с ровно N участниками."""
    with SessionLocal() as session:
        settings = session.get(DrawSettings, 1) or DrawSettings(id=1)
        session.add(settings)
        participants = list(
            session.scalars(
                select(User).where(
                    User.participation_status == "waiting_draw"
                )
            )
        )
        if settings.participant_limit is None or len(participants) != settings.participant_limit:
            raise ValueError("Количество участников не совпадает с лимитом.")

        weights = [user.losses_count + 1 for user in participants]
        total_weight = sum(weights)
        winner = random.choices(participants, weights=weights, k=1)[0]

        for user, weight in zip(participants, weights):
            user.winning_chance = Decimal(weight) / Decimal(total_weight)
            user.participation_status = "not_participating"
            user.payment_status = "not_paid"
            if user.telegram_id == winner.telegram_id:
                user.wins_count += 1
                user.losses_count = 0
            else:
                user.losses_count += 1

        session.add(
            DrawRound(
                winner_telegram_id=winner.telegram_id,
                participant_count=len(participants),
                total_weight=total_weight,
            )
        )
        settings.status = "completed"
        session.commit()
        return DrawResult(
            winner_telegram_id=winner.telegram_id,
            participants=participants,
            total_weight=total_weight,
        )


def get_users() -> list[User]:
    with SessionLocal() as session:
        return list(session.scalars(select(User).order_by(User.created_at.desc())))


def get_waiting_draw_count() -> int:
    with SessionLocal() as session:
        return len(
            list(
                session.scalars(
                    select(User.id).where(User.participation_status == "waiting_draw")
                )
            )
        )
