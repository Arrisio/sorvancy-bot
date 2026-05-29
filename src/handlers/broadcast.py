"""
Broadcast reply-keyboard button handlers (scenarios 11, 12).
Text and callback handling is in text_router.py and callback_router.py.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_PERM_TZ = ZoneInfo("Asia/Yekaterinburg")

from maxapi.types import MessageCreated
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import StaffState, RegistrationState
from src.keyboards import (
    broadcast_start_keyboard,
    broadcast_coupon_choice_keyboard,
    cancel_broadcast_keyboard,
    cancel_keyboard,
    superuser_keyboard,
    BROADCAST_CREATE_BTN_TEXT,
    BROADCAST_LIST_BTN_TEXT,
)
from src.db.connection import get_session_factory
from src.models import broadcast as broadcast_model
from src.models import staff as staff_model
from src.db.orm import Staff
from src.handlers.callbacks._common import _append_step_mid, _delete_step_mids
import config

logger = logging.getLogger(__name__)


def _in_window(dt: datetime) -> bool:
    local = dt.astimezone(_PERM_TZ)
    return config.BROADCAST_WINDOW_START_HOUR <= local.hour < config.BROADCAST_WINDOW_END_HOUR


def _nearest_window_slot() -> datetime:
    now = datetime.now(_PERM_TZ)
    start = config.BROADCAST_WINDOW_START_HOUR
    end = config.BROADCAST_WINDOW_END_HOUR
    if start <= now.hour < end:
        return now
    if now.hour < start:
        return now.replace(hour=start, minute=0, second=0, microsecond=0)
    return (now + timedelta(days=1)).replace(hour=start, minute=0, second=0, microsecond=0)


def _tomorrow_window_slot() -> datetime:
    now = datetime.now(_PERM_TZ)
    return (now + timedelta(days=1)).replace(
        hour=config.BROADCAST_WINDOW_START_HOUR, minute=0, second=0, microsecond=0
    )


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
        await context.update_data(step_mids=[])
        sent = await event.message.answer(
            "Шаг 1 из 4 · Пришлите сообщение для рассылки",
            attachments=[cancel_keyboard("broadcast:cancel_create")],
        )
        await _append_step_mid(context, sent.message.body.mid)

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
    user_id = event.message.sender.user_id
    mid = event.message.body.mid
    chat_id = getattr(event.message.recipient, "chat_id", None) or user_id
    await context.update_data(
        broadcast_source_mid=mid,
        broadcast_source_chat_id=chat_id,
    )
    await context.set_state(StaffState.AWAITING_BROADCAST_COUPON_CHOICE)
    sent = await event.bot.send_message(
        user_id=user_id,
        text="Шаг 2 из 4 · Добавить купон к рассылке?",
        attachments=[broadcast_coupon_choice_keyboard()],
    )
    await _append_step_mid(context, sent.message.body.mid)


async def _ask_broadcast_recipients(bot, user_id: int, context) -> None:
    await context.set_state(StaffState.AWAITING_BROADCAST_RECIPIENTS)
    sent = await bot.send_message(
        user_id=user_id,
        text="Шаг 3 из 4 · Пришлите номера клиентов для рассылки (через запятую или с новой строки):",
        attachments=[cancel_keyboard("broadcast:cancel_create")],
    )
    await _append_step_mid(context, sent.message.body.mid)


async def _create_broadcast(bot, user_id: int, context, scheduled_at: datetime):
    data = await context.get_data()
    mid = data.get("broadcast_source_mid")
    chat_id = data.get("broadcast_source_chat_id")
    recipient_ids = data.get("broadcast_recipient_ids", [])
    coupon_value = data.get("broadcast_coupon_value")
    coupon_days = data.get("broadcast_coupon_days")
    coupon_min_purchase = data.get("broadcast_coupon_min_purchase")
    coupon_display_name = data.get("broadcast_coupon_display_name")

    if not mid or not recipient_ids:
        await bot.send_message(user_id=user_id, text="Ошибка: нет данных для рассылки.")
        await context.set_state(RegistrationState.REGISTERED)
        return

    try:
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
                    status="pending",
                    coupon_value=coupon_value,
                    coupon_validity_days=coupon_days,
                    coupon_min_purchase_amount=coupon_min_purchase,
                    coupon_display_name=coupon_display_name,
                )
                await broadcast_model.create_recipients(session, b.id, recipient_ids)
    except Exception:
        logger.exception("Broadcast create failed")
        await bot.send_message(user_id=user_id, text="Ошибка при создании рассылки.")
        return

    await context.set_state(RegistrationState.REGISTERED)
    await _delete_step_mids(bot, context)
    dt_local = scheduled_at.astimezone(_PERM_TZ).strftime("%d.%m.%Y %H:%M")
    coupon_suffix = f" + купон на {coupon_value} ₽" if coupon_value else ""
    await bot.send_message(
        user_id=user_id,
        text=f"Рассылка #{b.id} запланирована на {dt_local}. Получателей: {len(recipient_ids)}{coupon_suffix}.",
        attachments=[superuser_keyboard()],
    )
