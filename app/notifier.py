import asyncio

from telegram import Bot

from app.config import TELEGRAM_BOT_TOKEN


async def send_telegram_message(chat_id: int, text: str) -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing in .env")

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=chat_id, text=text)


def send_telegram_message_sync(chat_id: int, text: str) -> None:
    asyncio.run(send_telegram_message(chat_id, text))
