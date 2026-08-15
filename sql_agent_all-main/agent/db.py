"""Connections to the two Postgres databases set up in docker/ (see
docker/docker-compose.yml and docker/README.md)."""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "docker" / ".env")

_engines: dict[str, Engine] = {}


def _connection_url(database: str) -> str:
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    port = os.environ["POSTGRES_PORT"]
    return f"postgresql+psycopg2://{user}:{password}@localhost:{port}/{database}"


def get_engine(database: str) -> Engine:
    if database not in _engines:
        _engines[database] = create_engine(_connection_url(database))
    return _engines[database]


def explain_query(database: str, sql: str) -> None:
    """Validates the query's syntax and schema references against the real
    database catalog without executing it, by running it through the planner.
    Raises on any error (bad table/column name, syntax error, etc.)."""
    engine = get_engine(database)
    with engine.connect() as conn:
        conn.execute(text(f"EXPLAIN {sql}"))


def run_query(database: str, sql: str) -> pd.DataFrame:
    engine = get_engine(database)
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn)
