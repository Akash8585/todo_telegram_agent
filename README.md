# todo-agent

Telegram reminder bot that turns natural language into scheduled tasks. It uses [Groq](https://groq.com/) (OpenAI-compatible API) to parse intents and times, stores tasks in SQLite via [SQLModel](https://sqlmodel.tiangolo.com/), and sends due reminders with inline **Done** and **Snooze** actions.

## Features

- **Natural language**: Phrases like “today at 5 pm meet friends”, “tomorrow 8 am gym”, “show my tasks”, mark-done and delete intents.
- **Commands**: `/start`, `/add`, `/tasks`, `/done`, `/delete` (see bot help text).
- **Recurring tasks**: Daily or weekly recurrence when the model sets the right fields.
- **Scheduler**: Background job every 30 seconds checks for due pending tasks and sends Telegram messages with buttons.
- **Small FastAPI app** (`app/main.py`): health-style root endpoint; database tables are created on startup.

## Requirements

- Python 3.10+ (uses `datetime.UTC`, `str | None`, etc.)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Groq API key from [Groq Console](https://console.groq.com/)

## Setup

1. Clone the repository and create a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies (no `requirements.txt` is checked in; install what the imports need):

   ```bash
   pip install fastapi uvicorn sqlmodel python-dotenv openai python-telegram-bot apscheduler
   ```

3. Copy or create a `.env` file in the project root:

   | Variable | Required | Description |
   |----------|----------|-------------|
   | `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
   | `GROQ_API_KEY` | Yes | Groq API key for the parser |
   | `GROQ_MODEL` | No | Loaded in `app/config.py`; the parser currently calls `llama-3.1-8b-instant` explicitly in `app/parser.py` |
   | `DATABASE_URL` | No | Default: `sqlite:///tasks.db` |
   | `TIMEZONE` | No | Default: `Asia/Kolkata` (used for parsing and display) |

## Run the bot

From the project root (with `app` as a package on `PYTHONPATH`):

```bash
python -m app.bot
```

This creates database tables, starts the APScheduler job, and begins long polling.

## Run the API (optional)

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` for a simple JSON status message.

## Project layout

| Path | Role |
|------|------|
| `app/bot.py` | Telegram handlers, commands, callbacks for snooze/done |
| `app/parser.py` | Groq chat completion → structured JSON intent |
| `app/routes/tasks.py` | Task CRUD, NL routing, snooze |
| `app/scheduler.py` | Due-task polling and reminder messages |
| `app/models.py` | `Task` SQLModel |
| `app/db.py` | Engine, sessions, `create_db_and_tables` |
| `app/config.py` | Environment loading |

## License

Add a license file if you intend to distribute this project.
