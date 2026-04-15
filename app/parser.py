import json
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.config import GROQ_API_KEY, TIMEZONE

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


def parse_user_message(user_input: str) -> dict:
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")

    system_prompt = f"""
You are an intent parser for a Telegram reminder bot.

Current local datetime: {today}
Timezone: {TIMEZONE}

Return ONLY valid JSON using this schema:
{{
  "intent": "create_task | list_tasks | mark_done | delete_task | unknown",
  "title": "task title or null",
  "due_at": "ISO-8601 datetime with timezone offset or null",
  "timezone": "{TIMEZONE}" or null,
  "task_id": integer or null
  "is_recurring": true or false,
  "recurrence_type": "daily | weekly | null",
  "recurrence_value": "daily | monday | tuesday | wednesday | thursday | friday | saturday | sunday | null"
}}

Rules:
- Return only JSON
- No markdown
- No explanation
- If the user wants to create a task, set intent=create_task
- If the user wants to see tasks, set intent=list_tasks
- If the user wants to mark a task completed, set intent=mark_done
- If the user wants to remove a task, set intent=delete_task
- If the task repeats every day, set is_recurring=true, recurrence_type="daily", recurrence_value="daily"
- If the task repeats weekly on a weekday, set is_recurring=true, recurrence_type="weekly", recurrence_value as the weekday in lowercase
- If the task does not repeat, set is_recurring=false and recurrence fields to null
- For recurring tasks, due_at should be the next upcoming occurrence in the user's timezone
- If unclear, set intent=unknown
- For create_task, clean the title
- Remove filler phrases like "remind me to", "i need to", "need to", "please remind me to"
- Keep only the actual task title
- Preserve meaning
- Interpret time relative to current local datetime
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
    )

    content = response.choices[0].message.content.strip()
    return json.loads(content)