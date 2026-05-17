import asyncio
from sqlalchemy import text

from src.db.connection import get_engine, get_session_factory
from src.db.orm import Base, Staff

MODEL = Staff
TABLE = MODEL.__table__


async def main():
    engine = get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(TABLE.drop, checkfirst=True)
        await conn.run_sync(TABLE.create)

    session_factory = get_session_factory()
    async with session_factory() as session:
        owner = Staff(
            max_user_id=38849435,
            username=None,
            first_name="Дмитрий",
            last_name="Сучков",
            phone="REDACTED_PHONE",
            is_owner=True,
        )
        session.add(owner)
        await session.commit()
        print(f"Created staff id={owner.id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
