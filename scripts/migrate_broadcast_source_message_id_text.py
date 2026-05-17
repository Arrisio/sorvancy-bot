"""Migration: change broadcasts.source_message_id from BIGINT to TEXT."""
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
                "ALTER TABLE broadcasts ALTER COLUMN source_message_id TYPE TEXT USING source_message_id::TEXT"
            ))
        print("Done: source_message_id changed to TEXT.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
