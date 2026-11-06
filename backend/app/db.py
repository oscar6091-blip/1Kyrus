"""SQLite engine. The schema is executed verbatim from handoff/contracts/database.sql.

Every connection gets foreign_keys and busy_timeout. Every transaction starts with
BEGIN IMMEDIATE so two writers cannot approve from the same stale read.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import CONTRACTS_DIR, settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _make_engine(url: str) -> Engine:
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 5})

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _record):  # noqa: ANN001
        dbapi_conn.isolation_level = None  # we issue BEGIN ourselves
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("PRAGMA busy_timeout = 5000")
        cur.execute("PRAGMA journal_mode = WAL")
        cur.close()

    @event.listens_for(engine, "begin")
    def _on_begin(conn):  # noqa: ANN001
        conn.exec_driver_sql("BEGIN IMMEDIATE")

    return engine


def init_engine(url: str | None = None) -> Engine:
    """(Re)create the engine; tests call this with a temp file."""
    global _engine, _SessionLocal
    url = url or settings.database_url
    path = url[len("sqlite:///"):]
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if _engine is not None:
        _engine.dispose()
    _engine = _make_engine(url)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    ddl = (CONTRACTS_DIR / "database.sql").read_text(encoding="utf-8")
    raw = _engine.raw_connection()
    try:
        raw.driver_connection.executescript(ddl)
    finally:
        raw.close()
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        init_engine()
    assert _engine is not None
    return _engine


@contextmanager
def tx() -> Iterator[Session]:
    """Short transaction: commit on success, roll back on error."""
    get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        with session.begin():
            yield session
    finally:
        session.close()
