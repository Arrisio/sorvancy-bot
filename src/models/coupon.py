from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import Coupon

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


async def create_survey_coupon(
    session: AsyncSession,
    customer_id: int,
    value: int,
    min_purchase: int,
    valid_days: int,
) -> Coupon:
    now = datetime.now(tz=timezone.utc)
    valid_until = now + timedelta(days=valid_days)
    display_name = f"Бонус {value} ₽ до {valid_until.strftime('%d.%m.%y')}"
    coupon = Coupon(
        customer_id=customer_id,
        type="anket",
        display_name=display_name,
        value=value,
        min_purchase_amount=min_purchase,
        valid_until=valid_until,
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
    min_purchase_amount: int,
    display_name: str,
) -> Coupon:
    now = datetime.now(tz=timezone.utc)
    coupon = Coupon(
        customer_id=customer_id,
        type="seller",
        display_name=display_name,
        value=value,
        min_purchase_amount=min_purchase_amount,
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
    min_purchase: int = 0,
) -> Coupon:
    now = datetime.now(tz=timezone.utc)
    valid_until = now + timedelta(days=valid_days)
    display_name = f"ДР: {value} ₽ до {valid_until.strftime('%d.%m.%y')}"
    coupon = Coupon(
        customer_id=customer_id,
        type="birthday",
        display_name=display_name,
        value=value,
        min_purchase_amount=min_purchase,
        valid_until=valid_until,
        status="active",
    )
    session.add(coupon)
    await session.flush()
    await session.refresh(coupon)
    return coupon


async def create_broadcast_coupon(
    session: AsyncSession,
    customer_id: int,
    value: int,
    validity_days: int,
    min_purchase_amount: int,
    display_name: str,
) -> Coupon:
    now = datetime.now(tz=timezone.utc)
    coupon = Coupon(
        customer_id=customer_id,
        type="broadcast",
        display_name=display_name,
        value=value,
        min_purchase_amount=min_purchase_amount,
        valid_until=now + timedelta(days=validity_days),
        status="active",
    )
    session.add(coupon)
    await session.flush()
    await session.refresh(coupon)
    return coupon


async def expire_coupons(session: AsyncSession) -> int:
    now = datetime.now(tz=timezone.utc)
    result = await session.execute(
        update(Coupon)
        .where(Coupon.status == "active", Coupon.valid_until <= now)
        .values(status="expired")
    )
    return result.rowcount


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
