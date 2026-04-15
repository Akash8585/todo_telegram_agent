from fastapi import FastAPI

from app.db import create_db_and_tables

app = FastAPI(title="Reminder Agent")

@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Reminder Agent is running"}