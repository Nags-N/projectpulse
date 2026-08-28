"""SQLAlchemy database setup and session management."""

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_data_dir() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)


_ensure_data_dir()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from backend.models import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def metadata_to_json(data: dict) -> str:
    return json.dumps(data)


def metadata_from_json(raw: str | None) -> dict:
    if not raw:
        return {}
    return json.loads(raw)
