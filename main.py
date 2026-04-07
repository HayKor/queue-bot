import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from app.router import router
from app import db

logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения Docker
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Не задана переменная окружения BOT_TOKEN!")

async def main():
    db.init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        # THIS GOES LAST
        await dp.start_polling(bot)

    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
