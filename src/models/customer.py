from datetime import date
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import Customer


async def get_by_max_id(session: AsyncSession, max_user_id: int) -> Optional[Customer]:
    result = await session.execute(
        select(Customer).where(Customer.max_user_id == max_user_id)
    )
    return result.scalar_one_or_none()


async def create(
    session: AsyncSession,
    max_user_id: int,
    max_username: Optional[str],
    discount_percent: int,
    first_name: Optional[str] = None,
) -> Customer:
    customer = Customer(
        max_user_id=max_user_id,
        max_username=max_username,
        first_name=first_name,
        discount_percent=discount_percent,
    )
    session.add(customer)
    await session.flush()
    await session.refresh(customer)
    return customer


async def update_survey_data(
    session: AsyncSession,
    max_user_id: int,
    first_name: str,
    birthdate: Optional[date],
) -> Optional[Customer]:
    await session.execute(
        update(Customer)
        .where(Customer.max_user_id == max_user_id)
        .values(first_name=first_name, birthdate=birthdate)
    )
    return await get_by_max_id(session, max_user_id)


async def is_registered(session: AsyncSession, max_user_id: int) -> bool:
    return await get_by_max_id(session, max_user_id) is not None
