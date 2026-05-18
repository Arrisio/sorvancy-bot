"""Create all tables if not exist. Safe on every deploy — no drops."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from src.db.connection import get_engine
from src.db.orm import Base, Staff, FinancialConfig


async def main():
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("DB schema up to date.")

        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            existing_cfg = await session.scalar(
                select(FinancialConfig).where(FinancialConfig.id == 1)
            )
            if not existing_cfg:
                session.add(FinancialConfig(id=1))
                await session.commit()
                print("FinancialConfig singleton row created with defaults.")
            else:
                print("FinancialConfig row already exists, skipping.")

        owner_id = os.environ.get("OWNER_ID")
        if owner_id:
            async with async_session() as session:
                existing = await session.scalar(
                    select(Staff).where(Staff.max_user_id == int(owner_id))
                )
                if not existing:
                    session.add(Staff(max_user_id=int(owner_id), is_owner=True))
                    await session.commit()
                    print(f"Owner staff record created (max_user_id={owner_id}).")
                else:
                    print("Owner staff record already exists, skipping.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
