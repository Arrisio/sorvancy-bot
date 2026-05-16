from datetime import date
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.db.orm import Child


async def create(
    session: AsyncSession,
    customer_id: int,
    name: str,
    gender: str,
    birthdate: date,
) -> Child:
    child = Child(customer_id=customer_id, name=name, gender=gender, birthdate=birthdate)
    session.add(child)
    await session.flush()
    await session.refresh(child)
    return child


async def get_by_customer(session: AsyncSession, customer_id: int) -> list[Child]:
    result = await session.execute(
        select(Child)
        .where(Child.customer_id == customer_id)
        .order_by(Child.birthdate)
    )
    return list(result.scalars())


async def get_upcoming_birthdays(session: AsyncSession, days_ahead: int = 7) -> list[Child]:
    now = func.now()
    deadline = now + text(f"INTERVAL '{int(days_ahead)} days'")
    result = await session.execute(
        select(Child)
        .options(joinedload(Child.customer))
        .where(
            func.to_char(Child.birthdate, "MM-DD").between(
                func.to_char(now, "MM-DD"),
                func.to_char(deadline, "MM-DD"),
            )
        )
    )
    return list(result.scalars())
