"""
Migration: repair broken server-side column defaults.

`server_default="NOW()"` was rendered by SQLAlchemy as the string literal
DEFAULT 'NOW()', which PostgreSQL coerced to timestamptz once at CREATE TABLE
time and froze as a constant. Every row inserted afterwards received the table
creation timestamp instead of the current time. Same class of bug for the
status columns, where server_default="'active'" produced DEFAULT '''active'''.

create_all() never alters existing tables, so the live DB needs these ALTERs.

Does NOT rewrite existing row data — see docs for the manual backfill.

Safe to run multiple times — skips columns that already look correct.

Run:
    python scripts/migrate_fix_column_defaults.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import config

_TIMESTAMP_COLUMNS = [
    ("customers", "registered_at"),
    ("children", "created_at"),
    ("staff", "created_at"),
    ("broadcasts", "created_at"),
]

_STATUS_COLUMNS = [
    ("coupons", "status", "active"),
    ("broadcast_recipients", "status", "pending"),
]


def _db_url() -> str:
    return (
        f"postgresql+asyncpg://{config.DB_USER}:{config.DB_PASSWORD}"
        f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )


async def _column_default(conn, table: str, column: str) -> str | None:
    result = await conn.execute(
        text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    row = result.fetchone()
    return row[0] if row else None


async def main():
    engine = create_async_engine(_db_url())
    try:
        async with engine.begin() as conn:
            for table, column in _TIMESTAMP_COLUMNS:
                current = await _column_default(conn, table, column)
                if current is None:
                    print(f"{table}.{column}: column missing — skipping.")
                    continue
                if "now()" in current.lower():
                    print(f"{table}.{column}: default already now() — skipping.")
                    continue
                await conn.execute(text(
                    f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT now()"
                ))
                print(f"{table}.{column}: default {current} -> now().")

            for table, column, value in _STATUS_COLUMNS:
                current = await _column_default(conn, table, column)
                if current is None:
                    print(f"{table}.{column}: column missing — skipping.")
                    continue
                if f"'{value}'::text" == current or current == f"'{value}'":
                    print(f"{table}.{column}: default already '{value}' — skipping.")
                    continue
                await conn.execute(text(
                    f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT '{value}'"
                ))
                print(f"{table}.{column}: default {current} -> '{value}'.")
                # Normalise rows that took the quoted literal.
                result = await conn.execute(text(
                    f"UPDATE {table} SET {column} = :v WHERE {column} = :bad"
                ), {"v": value, "bad": f"'{value}'"})
                if result.rowcount:
                    print(f"{table}.{column}: normalised {result.rowcount} row(s).")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
