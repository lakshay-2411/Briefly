from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

# Small pool: Supabase's free session pooler has a low connection limit.
pool = ConnectionPool(
    settings.database_url,
    min_size=1,
    max_size=5,
    open=False,
    check=ConnectionPool.check_connection,  # pooler drops idle connections
    kwargs={"autocommit": True, "row_factory": dict_row},
)


def fetch_one(sql: str, params: tuple | dict = ()) -> dict[str, Any] | None:
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchone()


def fetch_all(sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchall()


def execute(sql: str, params: tuple | dict = ()) -> int:
    with pool.connection() as conn:
        return conn.execute(sql, params).rowcount
