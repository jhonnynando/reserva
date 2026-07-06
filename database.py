from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import psycopg
import streamlit as st
from dotenv import load_dotenv
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
            "DATABASE_URL não configurada. Informe a connection string do Neon no .env ou nos secrets."
        )
    return url


@st.cache_resource(show_spinner=False)
def _connect(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url, row_factory=dict_row)


@st.cache_resource(show_spinner=False)
def _connection_lock() -> threading.RLock:
    return threading.RLock()


def get_connection() -> psycopg.Connection:
    conn = _connect(get_database_url())
    if conn.closed:
        _connect.clear()
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
        except Exception:
            conn.rollback()
            raise


def fetch_all(query: str, params: Params = None) -> list[dict[str, Any]]:
    with transaction() as cur:
        cur.execute(query, params or ())
        return list(cur.fetchall())


def fetch_one(query: str, params: Params = None) -> dict[str, Any] | None:
    with transaction() as cur:
        cur.execute(query, params or ())
        return cur.fetchone()


def execute(query: str, params: Params = None) -> None:
    with transaction() as cur:
        cur.execute(query, params or ())


def execute_returning(query: str, params: Params = None) -> dict[str, Any] | None:
    with transaction() as cur:
        cur.execute(query, params or ())
        return cur.fetchone()


def initialize_database() -> None:
    schema_path = Path(__file__).resolve().parent / "migrations" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    with transaction() as cur:
        cur.execute(schema_sql)

