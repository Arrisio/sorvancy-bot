"""
Broadcast reply-keyboard button handlers (scenarios 11, 12).
Text and callback handling is in text_router.py and callback_router.py.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_PERM_TZ = ZoneInfo("Asia/Yekaterinburg")

from maxapi.types import MessageCreated
from maxapi.types.message import NewMessageLink
from maxapi.enums.message_link_type import MessageLinkType
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import StaffState, RegistrationState
from src.keyboards import (
    broadcast_start_keyboard,
    cancel_broadcast_keyboard,
    cancel_keyboard,
    superuser_keyboard,
    BROADCAST_CREATE_BTN_TEXT,
    BROADCAST_LIST_BTN_TEXT,
)
from src.db.connection import get_session_factory
from src.models import broadcast as broadcast_model
from src.db.orm import Staff
import config

logger = logging.getLogger(__name__)


def _parse_scheduled_at(text: str) -> datetime | None:
    text = text.strip()
    m = re.match(r"(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})$", text)
    if m:
        d, mo, h, mi = int(m[1]), int(m[2]), int(m[3]), int(m[4])
        year = datetime.now(_PERM_TZ).year
        try:
            return datetime(year, mo, d, h, mi, tzinfo=_PERM_TZ)
        except ValueError:
            return None
    m = re.match(r"(\d{1,2})\.(\d{1,2})$", text)
    if m:
        d, mo = int(m[1]), int(m[2])
        year = datetime.now(_PERM_TZ).year
        try:
            return datetime(year, mo, d, 11, 0, tzinfo=_PERM_TZ)
        except ValueError:
            return None
    return None


async def register_broadcast_handlers(dp):

    @dp.message_created(F.message.body.text == BROADCAST_CREATE_BTN_TEXT)
    async def on_broadcast_create(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        route: str = "registration",
    ):
        if route != "staff" or staff is None or not staff.is_owner:
            return
        await context.set_state(StaffState.AWAITING_BROADCAST_MSG)
        await event.message.answer(
            "Пришлите сообщение для рассылки",
            attachments=[cancel_keyboard("broadcast:cancel_create")],
        )

    @dp.message_created(F.message.body.text == BROADCAST_LIST_BTN_TEXT)
    async def on_broadcast_list(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        route: str = "registration",
    ):
        if route != "staff" or staff is None or not staff.is_owner:
            return
        async with get_session_factory()() as session:
            pending = await broadcast_model.get_pending(session)
        if not pending:
            await event.message.answer("Нет запланированных рассылок.")
            return
        for b in pending:
            dt = b.scheduled_at.strftime("%d.%m.%Y %H:%M")
            await event.message.answer(
                f"Рассылка #{b.id}\nПолучателей: {b.recipient_count}\nЗапуск: {dt}",
                attachments=[cancel_broadcast_keyboard(b.id)],
            )


async def _save_broadcast_source(event, context) -> None:
    """Save broadcast source message reference and advance state to AWAITING_BROADCAST_RECIPIENTS."""
    user_id = event.message.sender.user_id
    mid = event.message.body.mid
    chat_id = getattr(event.message.recipient, "chat_id", None) or user_id
    await context.update_data(
        broadcast_source_mid=mid,
        broadcast_source_chat_id=chat_id,
    )
    await context.set_state(StaffState.AWAITING_BROADCAST_RECIPIENTS)
    await event.bot.send_message(
        user_id=user_id,
        text="Пришлите номера клиентов для рассылки (через запятую или с новой строки):",
        attachments=[cancel_keyboard("broadcast:cancel_create")],
    )


async def _create_broadcast(bot, user_id: int, context,
                            scheduled_at: datetime, status: str):
    data = await context.get_data()
    mid = data.get("broadcast_source_mid")
    chat_id = data.get("broadcast_source_chat_id")
    recipient_ids = data.get("broadcast_recipient_ids", [])

    if not mid or not recipient_ids:
        await bot.send_message(user_id=user_id, text="Ошибка: нет данных для рассылки.")
        await context.set_state(RegistrationState.REGISTERED)
        return

    try:
        from src.models import staff as staff_model
        async with get_session_factory()() as session:
            async with session.begin():
                staff_row = await staff_model.get_by_max_id(session, user_id)
                b = await broadcast_model.create(
                    session,
                    source_message_id=mid,
                    source_chat_id=chat_id or user_id,
                    created_by=staff_row.id if staff_row else None,
                    scheduled_at=scheduled_at,
                    recipient_count=len(recipient_ids),
                    status=status,
                )
                await broadcast_model.create_recipients(session, b.id, recipient_ids)
    except Exception:
        logger.exception("Broadcast create failed")
        await bot.send_message(user_id=user_id, text="Ошибка при создании рассылки.")
        return

    await context.set_state(RegistrationState.REGISTERED)
    if status == "running":
        await bot.send_message(
            user_id=user_id,
            text=f"Рассылка #{b.id} запущена. Получателей: {len(recipient_ids)}.",
            attachments=[superuser_keyboard()],
        )
        asyncio.create_task(_run_broadcast(bot, b.id, user_id))
    else:
        dt = scheduled_at.strftime("%d.%m.%Y %H:%M UTC")
        await bot.send_message(
            user_id=user_id,
            text=f"Рассылка #{b.id} запланирована на {dt}. Получателей: {len(recipient_ids)}.",
            attachments=[superuser_keyboard()],
        )


async def _run_broadcast(bot, broadcast_id: int, superuser_id: int):
    delay = config.BROADCAST_SEND_DELAY_SECONDS
    try:
        async with get_session_factory()() as session:
            recipients = await broadcast_model.get_pending_recipients(session, broadcast_id)
            broadcast_row = await broadcast_model.get_by_id(session, broadcast_id)

        if broadcast_row is None:
            return

        source_mid = broadcast_row.source_message_id

        for recipient in recipients:
            await asyncio.sleep(delay)
            max_user_id = recipient.customer.max_user_id if recipient.customer else None
            if max_user_id is None:
                logger.warning("Broadcast %s: no max_user_id for customer %s", broadcast_id, recipient.customer_id)
                async with get_session_factory()() as session:
                    await broadcast_model.mark_recipient_failed(session, recipient.id, "no max_user_id")
                continue
            try:
                await bot.send_message(
                    user_id=max_user_id,
                    link=NewMessageLink(type=MessageLinkType.FORWARD, mid=source_mid),
                )
                async with get_session_factory()() as session:
                    await broadcast_model.mark_recipient_sent(session, recipient.id)
            except Exception as e:
                logger.warning(
                    "Broadcast %s: failed for customer %s: %s",
                    broadcast_id, recipient.customer_id, e,
                )
                async with get_session_factory()() as session:
                    await broadcast_model.mark_recipient_failed(
                        session, recipient.id, str(e)
                    )

        async with get_session_factory()() as session:
            b = await broadcast_model.finish(session, broadcast_id)
        if b:
            await bot.send_message(
                user_id=superuser_id,
                text=(
                    f"Рассылка #{broadcast_id} завершена. "
                    f"Отправлено успешно: {b.sent_count}. "
                    f"Не удалось доставить: {b.failed_count}."
                ),
            )
    except Exception:
        logger.exception("Broadcast %s run failed", broadcast_id)
