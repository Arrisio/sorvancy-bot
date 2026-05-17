from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import Staff


async def get_by_max_id(session: AsyncSession, max_user_id: int) -> Optional[Staff]:
    result = await session.execute(
        select(Staff).where(Staff.max_user_id == max_user_id)
    )
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, staff_id: int) -> Optional[Staff]:
    result = await session.execute(select(Staff).where(Staff.id == staff_id))
    return result.scalar_one_or_none()


async def get_all_sellers(session: AsyncSession) -> list[Staff]:
    result = await session.execute(
        select(Staff).where(Staff.is_owner == False).order_by(Staff.created_at)
    )
    return list(result.scalars())


async def create(
    session: AsyncSession,
    max_user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    is_owner: bool = False,
) -> Staff:
    staff = Staff(
        max_user_id=max_user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        is_owner=is_owner,
    )
    session.add(staff)
    await session.flush()
    await session.refresh(staff)
    return staff


async def delete(session: AsyncSession, staff_id: int) -> None:
    staff = await get_by_id(session, staff_id)
    if staff:
        await session.delete(staff)


async def set_customer_mode(
    session: AsyncSession, max_user_id: int, value: bool
) -> Optional[Staff]:
    await session.execute(
        update(Staff)
        .where(Staff.max_user_id == max_user_id)
        .values(customer_mode=value)
    )
    return await get_by_max_id(session, max_user_id)
