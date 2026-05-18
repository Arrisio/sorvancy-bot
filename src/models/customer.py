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


async def get_by_id(session: AsyncSession, customer_id: int) -> Optional[Customer]:
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    return result.scalar_one_or_none()


async def get_all(session: AsyncSession) -> list[Customer]:
    result = await session.execute(select(Customer).order_by(Customer.id))
    return list(result.scalars())


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
    last_name: Optional[str],
    birthdate: Optional[date],
    phone: Optional[str],
    survey_completed: bool,
) -> Optional[Customer]:
    await session.execute(
        update(Customer)
        .where(Customer.max_user_id == max_user_id)
        .values(
            first_name=first_name,
            last_name=last_name,
            birthdate=birthdate,
            phone=phone,
            survey_completed=survey_completed,
        )
    )
    return await get_by_max_id(session, max_user_id)


async def update_field(
    session: AsyncSession, customer_id: int, **kwargs
) -> Optional[Customer]:
    await session.execute(
        update(Customer).where(Customer.id == customer_id).values(**kwargs)
    )
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    return result.scalar_one_or_none()


async def set_discount(
    session: AsyncSession, customer_id: int, discount_percent: int
) -> Optional[Customer]:
    return await update_field(session, customer_id, discount_percent=discount_percent)


async def toggle_opt_out(
    session: AsyncSession, customer_id: int
) -> Optional[Customer]:
    customer = await get_by_id(session, customer_id)
    if customer is None:
        return None
    return await update_field(
        session, customer_id, opt_out_marketing=not customer.opt_out_marketing
    )


async def save_survey_draft(
    session: AsyncSession,
    max_user_id: int,
    draft: dict,
) -> None:
    await session.execute(
        update(Customer)
        .where(Customer.max_user_id == max_user_id)
        .values(survey_draft=draft)
    )


async def clear_survey_draft(
    session: AsyncSession,
    max_user_id: int,
) -> None:
    await session.execute(
        update(Customer)
        .where(Customer.max_user_id == max_user_id)
        .values(survey_draft=None)
    )


async def is_registered(session: AsyncSession, max_user_id: int) -> bool:
    return await get_by_max_id(session, max_user_id) is not None


async def get_customers_for_birthday_reminder(
    session: AsyncSession, target_month: int, target_day: int
) -> list[Customer]:
    result = await session.execute(
        select(Customer).where(Customer.birthdate.isnot(None))
    )
    candidates = list(result.scalars())
    return [
        c for c in candidates
        if c.birthdate is not None
        and c.birthdate.month == target_month
        and c.birthdate.day == target_day
    ]


async def set_birthday_reminded_year(
    session: AsyncSession, customer_id: int, year: int
) -> None:
    await session.execute(
        update(Customer).where(Customer.id == customer_id).values(birthday_reminded_year=year)
    )
    await session.commit()
