from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings


def create_db_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)


engine = create_db_engine()


@contextmanager
def get_connection(db_engine: Engine | None = None):
    connection = (db_engine or engine).connect()
    try:
        yield connection
    finally:
        connection.close()
