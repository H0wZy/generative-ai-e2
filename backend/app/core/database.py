"""Database engine and session factory."""
from __future__ import annotations

import re

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _normalise_url(database_url: str) -> str:
    """Ensure we use psycopg (v3) driver — normalise postgresql:// prefix."""
    return re.sub(r"^postgresql://", "postgresql+psycopg://", str(database_url))


def make_engine(database_url: str):
    return create_engine(
        _normalise_url(database_url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = make_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
