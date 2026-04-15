from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.db import get_session
from app.models import Task
from app.parser import parse_user_message
from app.schemas import ParsedIntent


def add_task_for_user(telegram_user_id: int, raw_input: str) -> Task:
    """Parse as a create-task message; raises ValueError if not a valid new task."""
    try:
        result = handle_natural_language_message(telegram_user_id, raw_input)
    except ValueError:
        raise
    except Exception:
        raise ValueError("Could not parse task")

    if result.get("intent") != "create_task" or "task" not in result:
        raise ValueError("Could not parse task")

    return result["task"]


def list_tasks_for_user(telegram_user_id: int) -> list[Task]:
    with get_session() as session:
        statement = (
            select(Task)
            .where(Task.telegram_user_id == telegram_user_id)
            .where(Task.status == "pending")
            .order_by(Task.due_at)
        )
        return list(session.exec(statement).all())

def delete_task(telegram_user_id: int, task_id: int) -> bool:
    with get_session() as session:
        statement = select(Task).where(
            Task.id == task_id,
            Task.telegram_user_id == telegram_user_id
        )
        task = session.exec(statement).first()

        if not task:
            return False

        session.delete(task)
        session.commit()
        return True


def mark_task_done(telegram_user_id: int, task_id: int) -> Task | None:
    with get_session() as session:
        statement = select(Task).where(
            Task.id == task_id,
            Task.telegram_user_id == telegram_user_id
        )
        task = session.exec(statement).first()

        if not task:
            return None

        task.status = "done"
        task.reminder_sent = True

        session.add(task)
        session.commit()
        session.refresh(task)
        return task


def handle_natural_language_message(telegram_user_id: int, raw_input: str) -> dict:
    parsed_data = parse_user_message(raw_input)
    parsed = ParsedIntent(**parsed_data)

    if parsed.intent == "create_task":
        if not parsed.title or not parsed.due_at:
            raise ValueError("Missing title or due time")

        due_at_utc = parsed.due_at.astimezone(UTC)

        if due_at_utc <= datetime.now(UTC):
            raise ValueError("Task time is in the past")

        task = Task(
            telegram_user_id=telegram_user_id,
            title=parsed.title.strip(),
            raw_input=raw_input,
            due_at=due_at_utc,
            timezone=parsed.timezone or "Asia/Kolkata",
            status="pending",
            reminder_sent=False,
            is_recurring=bool(parsed.is_recurring),
            recurrence_type=parsed.recurrence_type,
            recurrence_value=parsed.recurrence_value,
        )

        with get_session() as session:
            session.add(task)
            session.commit()
            session.refresh(task)
            return {"intent": "create_task", "task": task}

    if parsed.intent == "list_tasks":
        tasks = list_tasks_for_user(telegram_user_id)
        return {"intent": "list_tasks", "tasks": tasks}

    if parsed.intent == "mark_done":
        if not parsed.task_id:
            raise ValueError("Missing task id")

        task = mark_task_done(telegram_user_id, parsed.task_id)
        return {"intent": "mark_done", "task": task}

    if parsed.intent == "delete_task":
        if not parsed.task_id:
            raise ValueError("Missing task id")

        success = delete_task(telegram_user_id, parsed.task_id)
        return {"intent": "delete_task", "success": success}

    return {"intent": "unknown"}



def snooze_task(telegram_user_id: int, task_id: int, minutes: int) -> Task | None:
    with get_session() as session:
        statement = select(Task).where(
            Task.id == task_id,
            Task.telegram_user_id == telegram_user_id
        )
        task = session.exec(statement).first()

        if not task:
            return None

        due_at = task.due_at
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=UTC)

        task.due_at = due_at + timedelta(minutes=minutes)
        task.reminder_sent = False
        task.status = "pending"

        session.add(task)
        session.commit()
        session.refresh(task)
        return task