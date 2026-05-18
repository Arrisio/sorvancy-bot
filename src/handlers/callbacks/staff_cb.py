import logging

from maxapi.context import MemoryContext

from src.states import StaffState, RegistrationState
from src.keyboards import (
    superuser_keyboard,
    staff_keyboard,
    cancel_keyboard,
    confirm_delete_seller_keyboard,
    confirm_coupon_keyboard,
    broadcast_cancel_confirm_keyboard,
)
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import coupon as coupon_model
from src.models import staff as staff_model
from src.models import broadcast as broadcast_model
from src.handlers.staff import _send_customer_profile_by_id
from src.handlers.broadcast import _create_broadcast, _nearest_window_slot, _ask_broadcast_recipients
from src.handlers.callbacks._common import _delete_step_mids, _append_step_mid, _display_name
from src.handlers.callbacks.financial_cb import handle_financial_callback

logger = logging.getLogger(__name__)


async def handle_staff_callback(event, context: MemoryContext, staff, state: str, payload: str, user_id: int) -> None:
    bot = event.bot

    if payload.startswith("financial:") and staff.is_owner:
        await handle_financial_callback(bot, user_id, state, payload, context)
        return

    if payload.startswith("seller:delete:") and staff.is_owner:
        staff_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            seller = await staff_model.get_by_id(session, staff_id)
        if seller is None:
            await bot.send_message(user_id=user_id, text="Продавец не найден.")
            return
        name = _display_name(seller.first_name, seller.last_name) or str(staff_id)
        await bot.send_message(
            user_id=user_id,
            text=f"Удалить продавца {name}? Это действие нельзя отменить.",
            attachments=[confirm_delete_seller_keyboard(staff_id)],
        )
        return

    if payload.startswith("seller:confirm_delete:") and staff.is_owner:
        staff_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            async with session.begin():
                await staff_model.delete(session, staff_id)
        await bot.send_message(
            user_id=user_id, text="Продавец удалён.", attachments=[superuser_keyboard()]
        )
        return

    if payload == "seller:cancel_delete":
        await bot.send_message(user_id=user_id, text="Удаление отменено.")
        return

    if payload == "find_customer:cancel":
        await context.set_state(RegistrationState.REGISTERED)
        kb = superuser_keyboard() if staff.is_owner else staff_keyboard()
        await bot.send_message(user_id=user_id, text="Отменено.", attachments=[kb])
        return

    if payload.startswith("discount:edit:"):
        customer_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            cust = await customer_model.get_by_id(session, customer_id)
        if cust is None:
            await bot.send_message(user_id=user_id, text="Клиент не найден.")
            return
        await context.update_data(
            editing_customer_id=customer_id,
            editing_customer_max_id=cust.max_user_id,
        )
        await context.set_state(StaffState.AWAITING_DISCOUNT_VALUE)
        await bot.send_message(
            user_id=user_id,
            text="Введите новое значение скидки (0–30):",
            attachments=[cancel_keyboard("discount:cancel")],
        )
        return

    if payload == "discount:cancel":
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(user_id=user_id, text="Отменено.")
        return

    if payload.startswith("coupon:redeem:"):
        coupon_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            c = await coupon_model.get_by_id(session, coupon_id)
        if c is None:
            await bot.send_message(user_id=user_id, text="Купон не найден.")
            return
        await bot.send_message(
            user_id=user_id,
            text=f"Использовать купон «{c.type}» ({c.value} ₽)?",
            attachments=[confirm_coupon_keyboard(coupon_id)],
        )
        return

    if payload.startswith("coupon:confirm:"):
        coupon_id = int(payload.split(":")[-1])
        cust = None
        async with get_session_factory()() as session:
            async with session.begin():
                c = await coupon_model.mark_used(session, coupon_id)
                if c is not None:
                    cust = await customer_model.get_by_id(session, c.customer_id)
        if c is None:
            await bot.send_message(user_id=user_id, text="Купон уже недействителен.")
            return
        await bot.send_message(user_id=user_id, text=f"Купон «{c.type}» использован.")
        if cust:
            try:
                await bot.send_message(
                    user_id=cust.max_user_id, text=f"Купон «{c.type}» использован."
                )
            except Exception:
                logger.warning("Could not notify customer %s of coupon use", cust.max_user_id)
        await _send_customer_profile_by_id(bot, user_id, c.customer_id)
        return

    if payload == "coupon:cancel":
        await bot.send_message(user_id=user_id, text="Отменено.")
        return

    if payload.startswith("coupon:issue:"):
        customer_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            cust = await customer_model.get_by_id(session, customer_id)
        if cust is None:
            await bot.send_message(user_id=user_id, text="Клиент не найден.")
            return
        name = _display_name(cust.first_name, cust.last_name) or str(customer_id)
        await context.update_data(coupon_target_customer_id=customer_id)
        await bot.send_message(
            user_id=user_id,
            text=f"Выдаёте купон клиенту {name}.",
            attachments=[cancel_keyboard("coupon:issue_cancel")],
        )
        await context.set_state(StaffState.AWAITING_COUPON_VALUE)
        await bot.send_message(
            user_id=user_id,
            text="Введите максимальную сумму купона (в рублях, 101–1000):",
            attachments=[cancel_keyboard("coupon:issue_cancel")],
        )
        return

    if payload == "coupon:issue_cancel":
        data = await context.get_data()
        coupon_ctx = data.get("coupon_context", "seller")
        if coupon_ctx == "broadcast":
            if state in (StaffState.AWAITING_COUPON_DAYS, StaffState.AWAITING_COUPON_PCT):
                await bot.send_message(
                    user_id=user_id,
                    text="Данные не сохранятся. Отменить рассылку?",
                    attachments=[broadcast_cancel_confirm_keyboard()],
                )
                return
            await context.set_state(RegistrationState.REGISTERED)
            await context.update_data(coupon_context=None)
            await _delete_step_mids(bot, context)
            await bot.send_message(user_id=user_id, text="Рассылка отменена.", attachments=[superuser_keyboard()])
        else:
            await context.set_state(RegistrationState.REGISTERED)
            customer_id = data.get("coupon_target_customer_id")
            if state in (StaffState.AWAITING_COUPON_DAYS, StaffState.AWAITING_COUPON_PCT) and customer_id:
                await bot.send_message(user_id=user_id, text="Выдача отменена.")
                await _send_customer_profile_by_id(bot, user_id, customer_id)
            else:
                await bot.send_message(user_id=user_id, text="Выдача купона отменена.")
        return

    if not staff.is_owner:
        return

    if payload == "broadcast:add_coupon":
        if state != StaffState.AWAITING_BROADCAST_COUPON_CHOICE:
            return
        await context.update_data(coupon_context="broadcast")
        await context.set_state(StaffState.AWAITING_COUPON_VALUE)
        sent = await bot.send_message(
            user_id=user_id,
            text="Введите максимальную сумму купона (в рублях, 101–1000):",
            attachments=[cancel_keyboard("coupon:issue_cancel")],
        )
        await _append_step_mid(context, sent.message.body.mid)
        return

    if payload == "broadcast:skip_coupon":
        if state != StaffState.AWAITING_BROADCAST_COUPON_CHOICE:
            return
        await _ask_broadcast_recipients(bot, user_id, context)
        return

    if payload == "broadcast:cancel_create":
        if state in (
            StaffState.AWAITING_COUPON_DAYS,
            StaffState.AWAITING_COUPON_PCT,
            StaffState.AWAITING_BROADCAST_RECIPIENTS,
            StaffState.AWAITING_BROADCAST_TIME,
        ):
            await bot.send_message(
                user_id=user_id,
                text="Данные не сохранятся. Отменить рассылку?",
                attachments=[broadcast_cancel_confirm_keyboard()],
            )
            return
        await context.set_state(RegistrationState.REGISTERED)
        await _delete_step_mids(bot, context)
        await bot.send_message(
            user_id=user_id, text="Рассылка отменена.",
            attachments=[superuser_keyboard()],
        )
        return

    if payload == "broadcast:confirm_cancel":
        await context.set_state(RegistrationState.REGISTERED)
        await context.update_data(coupon_context=None)
        await _delete_step_mids(bot, context)
        await bot.send_message(
            user_id=user_id, text="Рассылка отменена.",
            attachments=[superuser_keyboard()],
        )
        return

    if payload == "broadcast:continue":
        return

    if payload == "broadcast:soonest":
        if state != StaffState.AWAITING_BROADCAST_TIME:
            return
        await context.set_state(RegistrationState.REGISTERED)
        await _create_broadcast(bot, user_id, context, _nearest_window_slot())
        return

    if payload == "broadcast:cancel":
        if state not in (
            StaffState.AWAITING_BROADCAST_TIME,
            StaffState.AWAITING_BROADCAST_RECIPIENTS,
            StaffState.AWAITING_BROADCAST_MSG,
        ):
            return
        if state in (StaffState.AWAITING_BROADCAST_TIME, StaffState.AWAITING_BROADCAST_RECIPIENTS):
            await bot.send_message(
                user_id=user_id,
                text="Данные не сохранятся. Отменить рассылку?",
                attachments=[broadcast_cancel_confirm_keyboard()],
            )
            return
        await _delete_step_mids(bot, context)
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id, text="Рассылка отменена.",
            attachments=[superuser_keyboard()],
        )
        return

    if payload.startswith("broadcast:cancel:"):
        broadcast_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            async with session.begin():
                await broadcast_model.cancel(session, broadcast_id)
        await bot.send_message(
            user_id=user_id,
            text="Рассылка отмечена как «Отменена».",
            attachments=[superuser_keyboard()],
        )
        return
