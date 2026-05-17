from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import Broadcast, BroadcastRecipient, Customer, Staff


async def create(
    session: AsyncSession,
    source_message_id: str,
    source_chat_id: int,
    created_by: int,
    scheduled_at: datetime,
    recipient_count: int,
    status: str = "pending",
) -> Broadcast:
    broadcast = Broadcast(
        source_message_id=source_message_id,
        source_chat_id=source_chat_id,
        created_by=created_by,
        status=status,
        scheduled_at=scheduled_at,
        recipient_count=recipient_count,
    )
    session.add(broadcast)
    await session.flush()
    await session.refresh(broadcast)
    return broadcast


async def create_recipients(
    session: AsyncSession, broadcast_id: int, customer_ids: list[int]
) -> None:
    for cid in customer_ids:
        session.add(BroadcastRecipient(broadcast_id=broadcast_id, customer_id=cid))
    await session.flush()


async def get_by_id(session: AsyncSession, broadcast_id: int) -> Optional[Broadcast]:
    result = await session.execute(
        select(Broadcast).where(Broadcast.id == broadcast_id)
    )
    return result.scalar_one_or_none()


async def get_eligible_customer_ids(
    session: AsyncSession, customer_ids: list[int] | None = None
) -> list[int]:
    """Return customer IDs eligible for broadcast (opt_out_marketing = false)."""
    q = select(Customer.id).where(Customer.opt_out_marketing == False)
    if customer_ids is not None:
        q = q.where(Customer.id.in_(customer_ids))
    result = await session.execute(q)
    return list(result.scalars())


async def get_pending(session: AsyncSession) -> list[Broadcast]:
    result = await session.execute(
        select(Broadcast)
        .where(Broadcast.status == "pending")
        .order_by(Broadcast.scheduled_at)
    )
    return list(result.scalars())


async def get_due_pending_broadcasts(session: AsyncSession) -> list[Broadcast]:
    """Broadcasts with status=pending and scheduled_at <= now; ready to start delivery."""
    now = datetime.now(tz=timezone.utc)
    result = await session.execute(
        select(Broadcast)
        .where(Broadcast.status == "pending", Broadcast.scheduled_at <= now)
        .order_by(Broadcast.scheduled_at)
    )
    return list(result.scalars())


async def get_running_broadcasts_with_creator(session: AsyncSession) -> list[Broadcast]:
    """Broadcasts with status=running; includes creator Staff for notification."""
    result = await session.execute(
        select(Broadcast)
        .where(Broadcast.status == "running")
        .options(selectinload(Broadcast.creator))
    )
    return list(result.scalars())


async def set_status_running(session: AsyncSession, broadcast_id: int) -> None:
    await session.execute(
        update(Broadcast).where(Broadcast.id == broadcast_id).values(status="running")
    )
    await session.commit()


async def cancel(session: AsyncSession, broadcast_id: int) -> Optional[Broadcast]:
    await session.execute(
        update(Broadcast)
        .where(Broadcast.id == broadcast_id)
        .values(status="cancelled")
    )
    result = await session.execute(
        select(Broadcast).where(Broadcast.id == broadcast_id)
    )
    return result.scalar_one_or_none()


async def get_pending_recipients(
    session: AsyncSession, broadcast_id: int
) -> list[BroadcastRecipient]:
    result = await session.execute(
        select(BroadcastRecipient)
        .where(
            BroadcastRecipient.broadcast_id == broadcast_id,
            BroadcastRecipient.status == "pending",
        )
        .options(selectinload(BroadcastRecipient.customer))
    )
    return list(result.scalars())


async def mark_recipient_sent(
    session: AsyncSession, recipient_id: int
) -> None:
    now = datetime.now(tz=timezone.utc)
    await session.execute(
        update(BroadcastRecipient)
        .where(BroadcastRecipient.id == recipient_id)
        .values(status="sent", sent_at=now)
    )
    await session.commit()


async def mark_recipient_failed(
    session: AsyncSession, recipient_id: int, error: str
) -> None:
    await session.execute(
        update(BroadcastRecipient)
        .where(BroadcastRecipient.id == recipient_id)
        .values(status="failed", error=error)
    )
    await session.commit()


async def finish(session: AsyncSession, broadcast_id: int) -> Optional[Broadcast]:
    from sqlalchemy import func
    sent = await session.execute(
        select(func.count()).where(
            BroadcastRecipient.broadcast_id == broadcast_id,
            BroadcastRecipient.status == "sent",
        )
    )
    failed = await session.execute(
        select(func.count()).where(
            BroadcastRecipient.broadcast_id == broadcast_id,
            BroadcastRecipient.status == "failed",
        )
    )
    await session.execute(
        update(Broadcast)
        .where(Broadcast.id == broadcast_id)
        .values(
            status="completed",
            sent_count=sent.scalar(),
            failed_count=failed.scalar(),
        )
    )
    await session.commit()
    result = await session.execute(
        select(Broadcast).where(Broadcast.id == broadcast_id)
    )
    return result.scalar_one_or_none()
