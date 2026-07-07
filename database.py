from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import psycopg
import streamlit as st
from dotenv import load_dotenv
from psycopg import OperationalError
from psycopg.rows import dict_row

load_dotenv()

Params = Sequence[Any] | dict[str, Any] | None


class DatabaseConfigurationError(RuntimeError):
    """Raised when the application cannot find the Neon connection string."""


def get_setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from Streamlit secrets first, then from the local env."""
    load_dotenv(override=False)
    try:
        value = st.secrets.get(name)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def get_database_url() -> str:
    url = get_setting("DATABASE_URL")
    if not url:
        raise DatabaseConfigurationError(
            "DATABASE_URL nao configurada. Informe a connection string do Neon no .env ou nos secrets."
        )
    return url


@st.cache_resource(show_spinner=False)
def _connect(database_url: str) -> psycopg.Connection:
    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=15,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


@st.cache_resource(show_spinner=False)
def _connection_lock() -> threading.RLock:
    return threading.RLock()


def _discard_connection(conn: psycopg.Connection | None = None) -> None:
    try:
        if conn is not None and not conn.closed:
            conn.close()
    except Exception:
        pass
    _connect.clear()


def _connection_is_alive(conn: psycopg.Connection) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        conn.commit()
        return True
    except Exception:
        _discard_connection(conn)
        return False


def get_connection() -> psycopg.Connection:
    conn = _connect(get_database_url())
    if conn.closed or not _connection_is_alive(conn):
        _discard_connection(conn)
        conn = _connect(get_database_url())
    return conn


@contextmanager
def transaction() -> Iterator[psycopg.Cursor]:
    with _connection_lock():
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except OperationalError:
            _discard_connection(conn)
            raise
        except Exception:
            try:
                conn.rollback()
            except Exception:
                _discard_connection(conn)
            raise


def fetch_all(query: str, params: Params = None) -> list[dict[str, Any]]:
    for attempt in range(2):
        try:
            with transaction() as cur:
                cur.execute(query, params or ())
                return list(cur.fetchall())
        except OperationalError:
            if attempt == 1:
                raise
    return []


def fetch_one(query: str, params: Params = None) -> dict[str, Any] | None:
    for attempt in range(2):
        try:
            with transaction() as cur:
                cur.execute(query, params or ())
                return cur.fetchone()
        except OperationalError:
            if attempt == 1:
                raise
    return None


def execute(query: str, params: Params = None) -> None:
    for attempt in range(2):
        try:
            with transaction() as cur:
                cur.execute(query, params or ())
            return
        except OperationalError:
            if attempt == 1:
                raise


def execute_returning(query: str, params: Params = None) -> dict[str, Any] | None:
    for attempt in range(2):
        try:
            with transaction() as cur:
                cur.execute(query, params or ())
                return cur.fetchone()
        except OperationalError:
            if attempt == 1:
                raise
    return None


@st.cache_resource(show_spinner=False)
def initialize_database() -> None:
    schema_path = Path(__file__).resolve().parent / "migrations" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    with transaction() as cur:
        cur.execute(schema_sql)
