from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database import Base


class User(Base):
    """Пользователь Telegram-бота."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    participation_status: Mapped[str] = mapped_column(
        String(50), default="not_participating", nullable=False
    )
    participation_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    winning_chance: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("0.0000"), nullable=False
    )
    wins_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payment_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_status: Mapped[str] = mapped_column(
        String(50), default="not_paid", nullable=False
    )


class DrawSettings(Base):
    """Настройки единственного тестового розыгрыша MVP."""

    __tablename__ = "draw_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    draw_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    participant_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="not_started", nullable=False)


class DrawRound(Base):
    """История завершённого тестового розыгрыша."""

    __tablename__ = "draw_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    winner_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    participant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_weight: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
