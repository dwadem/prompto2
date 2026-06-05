from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.listing import Base

_engine = None
_SessionLocal = None


def _ensure_sqlite_dir(database_url: str) -> None:
    """SQLite creates the DB file but not its parent directory.

    On a fresh deploy (e.g. Railway) the ./data directory doesn't exist, so
    create_all() would fail with "unable to open database file". Make sure the
    directory exists first.
    """
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return
    db_path = url.database
    if not db_path or db_path == ":memory:":
        return
    parent = os.path.dirname(os.path.abspath(db_path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _ensure_sqlite_dir(settings.DATABASE_URL)
        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
        )
    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _SessionLocal


def init_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=_get_engine())


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    SessionLocal = _get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
