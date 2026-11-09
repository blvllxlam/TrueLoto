import asyncio
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.admin import router as admin_router
from bot.database import create_tables
from bot.handlers import router


async def main() -> None:
    load_dotenv()
    create_tables()
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise ValueError("BOT_TOKEN не найден. Добавьте его в файл .env.")

    bot = Bot(token=token)
    dispatcher = Dispatcher()
    dispatcher.include_router(admin_router)
    dispatcher.include_router(router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
