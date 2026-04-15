import asyncio
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import select
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from app.config import TELEGRAM_BOT_TOKEN, TIMEZONE
from app.db import get_session
from app.models import Task

scheduler = BackgroundScheduler(timezone="UTC")

WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def get_next_recurring_due(task: Task) -> datetime | None:
    due_at = task.due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)

    if not task.is_recurring:
        return None

    if task.recurrence_type == "daily":
        return due_at + timedelta(days=1)

    if task.recurrence_type == "weekly" and task.recurrence_value:
        current_local = due_at.astimezone(ZoneInfo(TIMEZONE))
        target_weekday = WEEKDAY_MAP.get(task.recurrence_value.lower())

        if target_weekday is None:
            return None

        days_ahead = (target_weekday - current_local.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7

        next_local = current_local + timedelta(days=days_ahead)
        return next_local.astimezone(UTC)

    return None


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

                next_due = get_next_recurring_due(task)

                if task.is_recurring and next_due:
                    task.due_at = next_due
                    task.reminder_sent = False
                else:
                    task.reminder_sent = True

                session.add(task)
                session.commit()
                print(f"[scheduler] reminder handled for task_id={task.id}")

            except TelegramError as e:
                session.rollback()
                print(f"[scheduler] telegram send failed for task_id={task.id}: {e}")
                t = session.get(Task, task.id)
                if t:
                    t.reminder_sent = True
                    session.add(t)
                    session.commit()

            except Exception as e:
                session.rollback()
                print(f"[scheduler] unexpected error for task_id={task.id}: {e}")
                t = session.get(Task, task.id)
                if t:
                    t.reminder_sent = True
                    session.add(t)
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
