from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_PATH = Path(__file__).resolve().parent.parent / "trueloto.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для моделей базы данных."""


def create_tables() -> None:
    """Создаёт таблицы и добавляет новые колонки в существующую БД."""
    from bot import models  # Импортирует модели перед созданием таблиц.

    Base.metadata.create_all(bind=engine)
    _add_user_columns()


def _add_user_columns() -> None:
    """Простая миграция для локальной SQLite-базы MVP."""
    columns_to_add = {
        "language_code": "VARCHAR(2)",
        "participation_status": "TEXT NOT NULL DEFAULT 'Не участвуете'",
        "participation_amount": "NUMERIC NOT NULL DEFAULT 0",
        "winning_chance": "NUMERIC NOT NULL DEFAULT 0",
        "wins_count": "INTEGER NOT NULL DEFAULT 0",
        "losses_count": "INTEGER NOT NULL DEFAULT 0",
        "payment_details": "TEXT",
        "payment_status": "TEXT NOT NULL DEFAULT 'not_paid'",
    }

    existing_columns = {
        column["name"] for column in inspect(engine).get_columns("users")
    }

    with engine.begin() as connection:
        for column_name, column_definition in columns_to_add.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}")
                )
