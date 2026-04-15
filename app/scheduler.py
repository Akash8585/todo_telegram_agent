import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import select
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from app.config import TELEGRAM_BOT_TOKEN, TIMEZONE
from app.db import get_session
from app.models import Task

scheduler = BackgroundScheduler(timezone="UTC")


def format_local_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local_dt = dt.astimezone(ZoneInfo(TIMEZONE))
    return local_dt.strftime("%d %b %Y, %I:%M %p")


async def send_reminder_with_buttons(chat_id: int, task: Task) -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing in .env")

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Done", callback_data=f"done:{task.id}"),
                InlineKeyboardButton("Snooze 10m", callback_data=f"snooze:{task.id}:10"),
            ],
            [
                InlineKeyboardButton("Snooze 1h", callback_data=f"snooze:{task.id}:60"),
            ],
        ]
    )

    message = (
        f"Reminder\n"
        f"#{task.id} • {task.title}\n"
        f"When: {format_local_time(task.due_at)}"
    )

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        reply_markup=keyboard,
    )


def check_due_tasks() -> None:
    now = datetime.now(UTC)

    with get_session() as session:
        statement = (
            select(Task)
            .where(Task.status == "pending")
            .where(Task.reminder_sent == False)
            .where(Task.due_at <= now)
        )

        due_tasks = session.exec(statement).all()

        for task in due_tasks:
            try:
                asyncio.run(send_reminder_with_buttons(task.telegram_user_id, task))
                task.reminder_sent = True
            except TelegramError as e:
                print(f"Telegram send failed for task {task.id}: {e}")
                task.reminder_sent = True
            except Exception as e:
                print(f"Unexpected send error for task {task.id}: {e}")
                task.reminder_sent = True

            session.add(task)

        session.commit()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(
            check_due_tasks,
            "interval",
            seconds=30,
            id="due-task-checker",
            replace_existing=True,
        )
        scheduler.start()
        print("Scheduler started...")
