"""Create all tables if not exist. Safe on every deploy — no drops."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.db.connection import get_engine
from src.db.orm import Base


async def main():
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("DB schema up to date.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
