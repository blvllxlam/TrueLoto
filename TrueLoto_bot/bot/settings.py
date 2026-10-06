import os


DEFAULT_DRAW_DATETIME = "31.12.2026 20:00 (UTC+4)"


def get_draw_datetime() -> str:
    """Возвращает дату тестового розыгрыша из настроек окружения."""
    return os.getenv("DRAW_DATETIME", DEFAULT_DRAW_DATETIME)


def get_admin_telegram_id() -> int | None:
    """Возвращает Telegram ID администратора из .env."""
    value = os.getenv("ADMIN_TELEGRAM_ID")
    return int(value) if value and value.isdigit() else None
