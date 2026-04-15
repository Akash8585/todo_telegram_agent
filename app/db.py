from sqlmodel import SQLModel, Session, create_engine

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
