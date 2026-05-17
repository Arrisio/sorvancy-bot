"""Migration: add survey_draft JSONB column to customers table."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import config


async def main():
    url = (
        f"postgresql+asyncpg://{config.DB_USER}:{config.DB_PASSWORD}"
        f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS survey_draft JSONB"
            ))
        print("Done: survey_draft column added to customers.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
