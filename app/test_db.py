from datetime import datetime, timedelta, UTC

from sqlmodel import select

from app.db import create_db_and_tables, get_session
from app.models import Task


def main() -> None:
    create_db_and_tables()

    task = Task(
        telegram_user_id=123456,
        title="Test task",
        raw_input="Test task at 6 PM",
        due_at=datetime.now(UTC) + timedelta(minutes=10),
        timezone="Asia/Kolkata",
    )

    with get_session() as session:
        session.add(task)
        session.commit()
        session.refresh(task)

        print("Saved task:")
        print(task)

        statement = select(Task)
        tasks = session.exec(statement).all()

        print("\nAll tasks:")
        for item in tasks:
            print(item)


if __name__ == "__main__":
    main()