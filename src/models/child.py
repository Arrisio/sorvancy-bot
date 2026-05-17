from datetime import date
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import Child, Customer


async def create(
    session: AsyncSession,
    customer_id: int,
    name: str,
    gender: str,
    birthdate: Optional[date],
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
        .order_by(Child.created_at)
    )
    return list(result.scalars())


async def get_by_id(session: AsyncSession, child_id: int) -> Optional[Child]:
    result = await session.execute(select(Child).where(Child.id == child_id))
    return result.scalar_one_or_none()


async def update_field(
    session: AsyncSession, child_id: int, **kwargs
) -> Optional[Child]:
    await session.execute(
        update(Child).where(Child.id == child_id).values(**kwargs)
    )
    return await get_by_id(session, child_id)


async def delete(session: AsyncSession, child_id: int) -> None:
    child = await get_by_id(session, child_id)
    if child:
        await session.delete(child)


async def get_children_for_birthday_reminder(
    session: AsyncSession, target_month: int, target_day: int
) -> list[Child]:
    """Return children whose birthdate month+day matches target, with customer eager-loaded."""
    result = await session.execute(
        select(Child)
        .where(Child.birthdate.isnot(None))
        .options(selectinload(Child.customer))
    )
    candidates = list(result.scalars())
    return [
        c for c in candidates
        if c.birthdate is not None
        and c.birthdate.month == target_month
        and c.birthdate.day == target_day
    ]


async def set_birthday_reminded_year(
    session: AsyncSession, child_id: int, year: int
) -> None:
    await session.execute(
        update(Child).where(Child.id == child_id).values(birthday_reminded_year=year)
    )
    await session.commit()
