from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel


class ParsedIntent(BaseModel):
    intent: Literal["create_task", "list_tasks", "mark_done", "delete_task", "unknown"]
    title: Optional[str] = None
    due_at: Optional[datetime] = None
    timezone: Optional[str] = None
    task_id: Optional[int] = None

    is_recurring: Optional[bool] = False
    recurrence_type: Optional[str] = None
    recurrence_value: Optional[str] = None