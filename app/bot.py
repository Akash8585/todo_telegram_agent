from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.config import TELEGRAM_BOT_TOKEN, TIMEZONE
from app.db import create_db_and_tables
from app.routes.tasks import (
    add_task_for_user,
    delete_task,
    handle_natural_language_message,
    list_tasks_for_user,
    mark_task_done,
    snooze_task,
)
from app.scheduler import start_scheduler


def format_local_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local_dt = dt.astimezone(ZoneInfo(TIMEZONE))
    return local_dt.strftime("%d %b %Y, %I:%M %p")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hello. I am your reminder bot.\n\n"
        "Commands:\n"
        "/add <task title>\n"
        "/tasks\n"
        "/done <task_id>\n"
        "/delete <task_id>"
    )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    telegram_user_id = update.effective_user.id
    raw_input = " ".join(context.args).strip()

    if not raw_input:
        await update.message.reply_text("Usage: /add <task with time>")
        return

    try:
        task = add_task_for_user(
            telegram_user_id=telegram_user_id,
            raw_input=raw_input,
        )

        await update.message.reply_text(
            f"Task saved.\n"
            f"ID: {task.id}\n"
            f"Title: {task.title}\n"
            f"Due at: {format_local_time(task.due_at)}"
        )

    except ValueError as e:
        print("Error:", e)
        msg = str(e)
        if msg == "Task time is in the past":
            await update.message.reply_text(
                "That time is already in the past. Use a future date and time."
            )
        else:
            await update.message.reply_text(
                "I could not understand the task time. Try again."
            )
    except Exception as e:
        print("Error:", e)
        await update.message.reply_text("Something went wrong. Try again.")


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    telegram_user_id = update.effective_user.id
    tasks = list_tasks_for_user(telegram_user_id)

    if not tasks:
        await update.message.reply_text("No pending tasks.")
        return

    lines = ["Your pending tasks:"]
    for task in tasks:
        lines.append(f"{task.id}. {task.title} | due: {format_local_time(task.due_at)}")

    await update.message.reply_text("\n".join(lines))


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    telegram_user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /done <task_id>")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Task ID must be a number.")
        return

    task = mark_task_done(telegram_user_id=telegram_user_id, task_id=task_id)

    if not task:
        await update.message.reply_text("Task not found.")
        return

    await update.message.reply_text(f"Task {task.id} marked as done.")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    telegram_user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /delete <task_id>")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Task ID must be a number.")
        return

    success = delete_task(telegram_user_id, task_id)

    if not success:
        await update.message.reply_text("Task not found.")
        return

    await update.message.reply_text(f"Task {task_id} deleted.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    telegram_user_id = update.effective_user.id
    raw_input = update.message.text.strip()

    try:
        result = handle_natural_language_message(
            telegram_user_id=telegram_user_id,
            raw_input=raw_input,
        )

        intent = result["intent"]

        if intent == "create_task":
            task = result["task"]
            await update.message.reply_text(
                f"Task created.\n"
                f"{task.id} • {task.title}\n"
                f"Due at: {format_local_time(task.due_at)}"
            )
            return

        if intent == "list_tasks":
            tasks = result["tasks"]
            if not tasks:
                await update.message.reply_text("You have no pending tasks.")
                return

            lines = ["Your pending tasks:"]
            for task in tasks:
                lines.append(
                    f"{task.id} • {task.title}\n"
                    f"   When: {format_local_time(task.due_at)}"
                )

            await update.message.reply_text("\n".join(lines))
            return

        if intent == "mark_done":
            task = result["task"]
            if not task:
                await update.message.reply_text("I could not find that task.")
                return

            await update.message.reply_text(f"Marked done: #{task.id} • {task.title}")
            return

        if intent == "delete_task":
            success = result["success"]
            if not success:
                await update.message.reply_text("I could not find that task.")
                return

            await update.message.reply_text("Task deleted.")
            return

        await update.message.reply_text(
            "I did not understand that fully.\n\n"
            " Try something like:\n"
            "- today at 5 pm need to meet friends\n"
            "- show my tasks\n"
            "- mark task 2 as done\n"
            "- delete task 3"
        )

    except Exception as e:
        print("Natural language error:", e)

        msg = str(e).lower()

        if "past" in msg:
            await update.message.reply_text(
                "That time is already in the past. Please send a future time."
            )
            return

        await update.message.reply_text(
            "I could not understand that.\n\n"
            "Try something like:\n"
            "- today at 5 pm need to meet friends\n"
            "- tomorrow 7 am gym\n"
            "- show my tasks"
        )


async def reminder_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    telegram_user_id = query.from_user.id
    data = query.data or ""

    try:
        parts = data.split(":")
        action = parts[0]

        if action == "done":
            task_id = int(parts[1])
            task = mark_task_done(telegram_user_id, task_id)

            if not task:
                await query.edit_message_text("I could not find that task.")
                return

            await query.edit_message_text(f"Done: #{task.id} • {task.title}")
            return

        if action == "snooze":
            task_id = int(parts[1])
            minutes = int(parts[2])

            task = snooze_task(telegram_user_id, task_id, minutes)

            if not task:
                await query.edit_message_text("I could not find that task.")
                return

            await query.edit_message_text(
                f"Snoozed: #{task.id} • {task.title}\n"
                f"New time: {format_local_time(task.due_at)}"
            )
            return

        await query.edit_message_text("Unknown action.")

    except Exception as e:
        print("Callback error:", e)
        await query.edit_message_text("Could not process that action.")


def run_bot() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing in .env")

    create_db_and_tables()
    start_scheduler()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CallbackQueryHandler(reminder_action_callback, pattern=r"^(done|snooze):"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()