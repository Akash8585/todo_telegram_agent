from datetime import datetime, UTC
from typing import Optional

from sqlmodel import SQLModel, Field


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_user_id: int
    title: str
    raw_input: str
    due_at: datetime
    timezone: str = "Asia/Kolkata"
    status: str = "pending"
    reminder_sent: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    is_recurring: bool = False
    recurrence_type: Optional[str] = None
    recurrence_value: Optional[str] = None
