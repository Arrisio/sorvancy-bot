"""
Background asyncio scheduler tasks.
  - broadcast_delivery_loop: hourly, delivers pending scheduled broadcasts (scenario 18)
  - birthday_reminder_loop: daily, sends birthday reminders 3 days before (scenario 19)
"""
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_PERM_TZ = ZoneInfo("Asia/Yekaterinburg")

import pymorphy3

import config
from src.db.connection import get_session_factory
from src.models import broadcast as broadcast_model
from src.models import child as child_model
from src.models import coupon as coupon_model
from src.models import customer as customer_model
from maxapi.types.message import NewMessageLink
from maxapi.enums.message_link_type import MessageLinkType
from src.services.discount import coupon_issued_notification

logger = logging.getLogger(__name__)

_morph = pymorphy3.MorphAnalyzer()

BROADCAST_DELIVERY_INTERVAL = 3600  # seconds
BIRTHDAY_CHECK_INTERVAL = 86400     # seconds
COUPON_EXPIRY_INTERVAL = 86400      # seconds


def _to_genitive(name: str) -> str:
    parsed = _morph.parse(name)
    if not parsed:
        return name
    inflected = parsed[0].inflect({"gent"})
    if inflected is None:
        return name
    return inflected.word.capitalize()


async def _deliver_broadcast(bot, broadcast) -> None:
    delay = config.BROADCAST_SEND_DELAY_SECONDS
    source_mid = broadcast.source_message_id
    creator_max_id: int | None = None
    if broadcast.creator:
        creator_max_id = broadcast.creator.max_user_id
    elif config.OWNER_ID:
        creator_max_id = config.OWNER_ID

    async with get_session_factory()() as session:
        recipients = await broadcast_model.get_pending_recipients(session, broadcast.id)

    for recipient in recipients:
        await asyncio.sleep(delay)
        max_user_id = recipient.customer.max_user_id if recipient.customer else None
        if max_user_id is None:
            logger.warning("Scheduler broadcast %s: no max_user_id for customer %s", broadcast.id, recipient.customer_id)
            async with get_session_factory()() as session:
                await broadcast_model.mark_recipient_failed(session, recipient.id, "no max_user_id")
            continue
        forward_ok = False
        try:
            await bot.send_message(
                user_id=max_user_id,
                link=NewMessageLink(type=MessageLinkType.FORWARD, mid=source_mid),
            )
            async with get_session_factory()() as session:
                await broadcast_model.mark_recipient_sent(session, recipient.id)
            forward_ok = True
        except Exception as e:
            logger.warning("Scheduler broadcast %s: failed for customer %s: %s", broadcast.id, recipient.customer_id, e)
            async with get_session_factory()() as session:
                await broadcast_model.mark_recipient_failed(session, recipient.id, str(e))

        if forward_ok and broadcast.coupon_value is not None and recipient.customer:
            try:
                async with get_session_factory()() as session:
                    async with session.begin():
                        coupon = await coupon_model.create_broadcast_coupon(
                            session,
                            customer_id=recipient.customer.id,
                            value=broadcast.coupon_value,
                            validity_days=broadcast.coupon_validity_days,
                            max_payment_pct=broadcast.coupon_max_payment_pct,
                        )
                await bot.send_message(
                    user_id=max_user_id,
                    text=coupon_issued_notification(coupon),
                )
            except Exception:
                logger.warning("Broadcast %s: coupon failed for customer %s", broadcast.id, recipient.customer_id)

    async with get_session_factory()() as session:
        b = await broadcast_model.finish(session, broadcast.id)

    if b and creator_max_id:
        try:
            await bot.send_message(
                user_id=creator_max_id,
                text=(
                    f"Рассылка #{broadcast.id} завершена. "
                    f"Отправлено успешно: {b.sent_count}. "
                    f"Не удалось доставить: {b.failed_count}."
                ),
            )
        except Exception:
            logger.warning("Scheduler: could not notify creator for broadcast %s", broadcast.id)


async def broadcast_delivery_loop(bot) -> None:
    while True:
        try:
            async with get_session_factory()() as session:
                due = await broadcast_model.get_due_pending_broadcasts(session)
                for b in due:
                    await broadcast_model.set_status_running(session, b.id)

            async with get_session_factory()() as session:
                running = await broadcast_model.get_running_broadcasts_with_creator(session)

            for broadcast in running:
                asyncio.create_task(_deliver_broadcast(bot, broadcast))

        except Exception:
            logger.exception("broadcast_delivery_loop error")

        await asyncio.sleep(BROADCAST_DELIVERY_INTERVAL)


async def coupon_expiry_loop() -> None:
    while True:
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    count = await coupon_model.expire_coupons(session)
            if count:
                logger.info("Coupon expiry: marked %d coupons as expired", count)
        except Exception:
            logger.exception("coupon_expiry_loop error")
        await asyncio.sleep(COUPON_EXPIRY_INTERVAL)


async def birthday_reminder_loop(bot) -> None:
    while True:
        try:
            await _run_birthday_reminders(bot)
        except Exception:
            logger.exception("birthday_reminder_loop error")
        await asyncio.sleep(BIRTHDAY_CHECK_INTERVAL)


async def _run_birthday_reminders(bot) -> None:
    today = datetime.now(_PERM_TZ).date()
    target = today + timedelta(days=3)
    target_year = target.year

    async with get_session_factory()() as session:
        children = await child_model.get_children_for_birthday_reminder(
            session, target.month, target.day
        )

    for child in children:
        if child.birthdate is None:
            continue

        upcoming_age = target_year - child.birthdate.year
        if upcoming_age >= 18:
            continue

        if child.birthday_reminded_year == target_year:
            continue

        cust = child.customer
        if cust is None or cust.max_user_id is None:
            continue

        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    coupon = await coupon_model.create_birthday_coupon(
                        session,
                        customer_id=cust.id,
                        value=config.BIRTHDAY_COUPON_VALUE,
                        valid_days=config.BIRTHDAY_COUPON_VALID_DAYS,
                    )

            name_gent = _to_genitive(child.name)
            valid_until_str = coupon.valid_until.astimezone(_PERM_TZ).strftime("%d.%m.%Y")

            await bot.send_message(
                user_id=cust.max_user_id,
                text=(
                    f"У {name_gent} через три дня день рождения. "
                    f"Вот вам купон на скидку — {config.BIRTHDAY_COUPON_VALUE} руб., "
                    f"действителен до {valid_until_str}."
                ),
            )

            async with get_session_factory()() as session:
                await child_model.set_birthday_reminded_year(session, child.id, target_year)

        except Exception:
            logger.exception("Birthday reminder failed for child %s", child.id)
