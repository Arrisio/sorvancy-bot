"""
Migration: add comment column to broadcasts table.

Safe to run multiple times — skips column if it already exists.

Run:
    python scripts/migrate_broadcast_comment.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import config


def _db_url() -> str:
    return (
        f"postgresql+asyncpg://{config.DB_USER}:{config.DB_PASSWORD}"
        f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )


async def _column_exists(conn, table: str, column: str) -> bool:
    result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.fetchone() is not None


async def main():
    engine = create_async_engine(_db_url())
    try:
        async with engine.begin() as conn:
            if await _column_exists(conn, "broadcasts", "comment"):
                print("broadcasts.comment already exists — skipping.")
            else:
                await conn.execute(text("ALTER TABLE broadcasts ADD COLUMN comment TEXT"))
                print("broadcasts.comment: added.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
