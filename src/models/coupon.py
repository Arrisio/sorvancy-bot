from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import Coupon

SURVEY_COUPON_VALUE = 300
SURVEY_COUPON_MAX_PCT = 30
SURVEY_COUPON_VALID_DAYS = 30


async def get_active_by_customer(session: AsyncSession, customer_id: int) -> list[Coupon]:
    now = datetime.now(tz=timezone.utc)
    result = await session.execute(
        select(Coupon).where(
            Coupon.customer_id == customer_id,
            Coupon.status == "active",
            Coupon.valid_until > now,
        )
    )
    return list(result.scalars())


async def get_by_id(session: AsyncSession, coupon_id: int) -> Optional[Coupon]:
    result = await session.execute(select(Coupon).where(Coupon.id == coupon_id))
    return result.scalar_one_or_none()


async def create_survey_coupon(session: AsyncSession, customer_id: int) -> Coupon:
    now = datetime.now(tz=timezone.utc)
    coupon = Coupon(
        customer_id=customer_id,
        type="anket",
        value=SURVEY_COUPON_VALUE,
        max_payment_pct=SURVEY_COUPON_MAX_PCT,
        valid_until=now + timedelta(days=SURVEY_COUPON_VALID_DAYS),
        status="active",
    )
    session.add(coupon)
    await session.flush()
    await session.refresh(coupon)
    return coupon


async def create_seller_coupon(
    session: AsyncSession,
    customer_id: int,
    value: int,
    validity_days: int,
    max_payment_pct: int,
) -> Coupon:
    now = datetime.now(tz=timezone.utc)
    coupon = Coupon(
        customer_id=customer_id,
        type="seller",
        value=value,
        max_payment_pct=max_payment_pct,
        valid_until=now + timedelta(days=validity_days),
        status="active",
    )
    session.add(coupon)
    await session.flush()
    await session.refresh(coupon)
    return coupon


async def create_birthday_coupon(
    session: AsyncSession,
    customer_id: int,
    value: int,
    valid_days: int,
    max_payment_pct: int = 100,
) -> Coupon:
    now = datetime.now(tz=timezone.utc)
    coupon = Coupon(
        customer_id=customer_id,
        type="birthday",
        value=value,
        max_payment_pct=max_payment_pct,
        valid_until=now + timedelta(days=valid_days),
        status="active",
    )
    session.add(coupon)
    await session.flush()
    await session.refresh(coupon)
    return coupon


async def mark_used(session: AsyncSession, coupon_id: int) -> Optional[Coupon]:
    now = datetime.now(tz=timezone.utc)
    result = await session.execute(
        select(Coupon).where(
            Coupon.id == coupon_id,
            Coupon.status == "active",
            Coupon.valid_until > now,
        )
    )
    coupon = result.scalar_one_or_none()
    if coupon is None:
        return None
    await session.execute(
        update(Coupon)
        .where(Coupon.id == coupon_id)
        .values(status="used", used_at=now)
    )
    return coupon
