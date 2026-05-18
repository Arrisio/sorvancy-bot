"""
Single unified handler for all message_callback events.
Routes to sub-handlers based on `route`, `staff`, and FSM state.
"""
import logging
from datetime import date, datetime

from maxapi.types import MessageCallback
from maxapi.context import MemoryContext

from src.states import RegistrationState, ProfileState, StaffState
from src.db.orm import Customer, Staff
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model
from src.models import coupon as coupon_model
from src.models import staff as staff_model
from src.models import broadcast as broadcast_model
from src.keyboards import (
    registered_keyboard,
    staff_keyboard,
    superuser_keyboard,
    back_keyboard,
    back_and_skip_keyboard,
    gender_keyboard,
    buy_for_self_keyboard,
    yes_no_keyboard,
    confirmation_card_keyboard,
    contact_keyboard,
    profile_card_keyboard,
    children_list_keyboard,
    child_card_keyboard,
    confirm_delete_child_keyboard,
    adding_child_back_keyboard,
    staff_profile_keyboard,
    confirm_coupon_keyboard,
    delete_seller_keyboard,
    confirm_delete_seller_keyboard,
    cancel_keyboard,
    broadcast_start_keyboard,
    cancel_broadcast_keyboard,
    resume_survey_keyboard,
)
from src.handlers.registration import _format_confirmation, _parse_date
from src.handlers.profile import _profile_text, _child_text
from src.handlers.broadcast import _create_broadcast, _parse_scheduled_at, _nearest_window_slot, _ask_broadcast_recipients
from src.handlers.staff import _send_customer_profile_by_id
from src.services.discount import coupon_issued_notification

logger = logging.getLogger(__name__)


async def _append_step_mid(context: MemoryContext, mid: str) -> None:
    data = await context.get_data()
    mids = list(data.get("step_mids") or [])
    mids.append(mid)
    await context.update_data(step_mids=mids)


async def _delete_step_mids(bot, context: MemoryContext) -> None:
    data = await context.get_data()
    for mid in (data.get("step_mids") or []):
        try:
            await bot.delete_message(message_id=mid)
        except Exception:
            pass
    await context.update_data(step_mids=[])


async def register_callback_router(dp):

    @dp.message_callback()
    async def unified_callback_handler(
        event: MessageCallback,
        context: MemoryContext,
        route: str = "registration",
        customer: Customer | None = None,
        staff: Staff | None = None,
    ):
        payload = event.callback.payload
        user_id = event.callback.user.user_id
        state = await context.get_state()

        await event.bot.send_callback(
            callback_id=event.callback.callback_id, notification="Принято"
        )

        if route == "staff" and staff is not None:
            await _handle_staff_callback(
                event, context, staff, state, payload, user_id
            )
        else:
            await _handle_customer_callback(
                event, context, customer, state, payload, user_id
            )


# --- Staff callbacks ---

async def _handle_staff_callback(event, context, staff, state, payload, user_id):
    bot = event.bot

    # Scenario 09: manage sellers
    if payload.startswith("seller:delete:") and staff.is_owner:
        staff_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            seller = await staff_model.get_by_id(session, staff_id)
        if seller is None:
            await bot.send_message(user_id=user_id, text="Продавец не найден.")
            return
        name = " ".join(filter(None, [seller.first_name, seller.last_name])) or str(staff_id)
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

    # Scenario 10: cancel customer ID lookup
    if payload == "find_customer:cancel":
        await context.set_state(RegistrationState.REGISTERED)
        kb = superuser_keyboard() if staff.is_owner else staff_keyboard()
        await bot.send_message(user_id=user_id, text="Отменено.", attachments=[kb])
        return

    # Scenario 07: edit discount
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

    # Scenario 08: redeem coupon
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
        async with get_session_factory()() as session:
            async with session.begin():
                c = await coupon_model.mark_used(session, coupon_id)
        if c is None:
            await bot.send_message(user_id=user_id, text="Купон уже недействителен.")
            return
        await bot.send_message(user_id=user_id, text=f"Купон «{c.type}» использован.")
        async with get_session_factory()() as session:
            cust = await customer_model.get_by_id(session, c.customer_id)
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

    # Scenario 15: issue seller coupon
    if payload.startswith("coupon:issue:"):
        customer_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            cust = await customer_model.get_by_id(session, customer_id)
        if cust is None:
            await bot.send_message(user_id=user_id, text="Клиент не найден.")
            return
        name = " ".join(filter(None, [cust.first_name or "", cust.last_name or ""])) or str(customer_id)
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
        await context.set_state(RegistrationState.REGISTERED)
        if coupon_ctx == "broadcast":
            await context.update_data(coupon_context=None)
            await _delete_step_mids(bot, context)
            await bot.send_message(user_id=user_id, text="Рассылка отменена.", attachments=[superuser_keyboard()])
        else:
            customer_id = data.get("coupon_target_customer_id")
            if state in (StaffState.AWAITING_COUPON_DAYS, StaffState.AWAITING_COUPON_PCT) and customer_id:
                await bot.send_message(user_id=user_id, text="Выдача отменена.")
                await _send_customer_profile_by_id(bot, user_id, customer_id)
            else:
                await bot.send_message(user_id=user_id, text="Выдача купона отменена.")
        return

    # Broadcast callbacks (owner only)
    if staff.is_owner:
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
            await _append_step_mid(context, sent.message.mid)
            return

        if payload == "broadcast:skip_coupon":
            if state != StaffState.AWAITING_BROADCAST_COUPON_CHOICE:
                return
            await _ask_broadcast_recipients(bot, user_id, context)
            return

        if payload == "broadcast:cancel_create":
            await context.set_state(RegistrationState.REGISTERED)
            await _delete_step_mids(bot, context)
            await bot.send_message(
                user_id=user_id, text="Рассылка отменена.",
                attachments=[superuser_keyboard()],
            )
            return

        if payload == "broadcast:soonest":
            if state != StaffState.AWAITING_BROADCAST_TIME:
                return
            await context.set_state(RegistrationState.REGISTERED)
            await _create_broadcast(bot, user_id, context, _nearest_window_slot())
            return

        if payload == "broadcast:cancel":
            if state not in (StaffState.AWAITING_BROADCAST_TIME, StaffState.AWAITING_BROADCAST_RECIPIENTS, StaffState.AWAITING_BROADCAST_MSG):
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


# --- Customer callbacks ---

async def _handle_customer_callback(event, context, customer, state, payload, user_id):
    bot = event.bot

    async def get_customer():
        nonlocal customer
        if customer is None:
            async with get_session_factory()() as session:
                customer = await customer_model.get_by_max_id(session, user_id)
        return customer

    # Survey callbacks
    if payload == "survey:start":
        async with get_session_factory()() as session:
            cust = await customer_model.get_by_max_id(session, user_id)
        if not cust:
            return
        data = await context.get_data()
        mid = data.get("survey_offer_mid")
        if mid:
            try:
                await bot.delete_message(message_id=mid)
            except Exception:
                pass
        if cust.survey_completed:
            async with get_session_factory()() as session:
                children = await child_model.get_by_customer(session, cust.id)
            await bot.send_message(
                user_id=user_id,
                text=_profile_text(cust, children),
                attachments=[profile_card_keyboard(cust.opt_out_marketing)],
            )
            return
        if cust.survey_draft and not cust.survey_completed:
            await bot.send_message(
                user_id=user_id,
                text=_format_resume_message(cust.survey_draft),
                attachments=[resume_survey_keyboard()],
            )
            return
        await context.update_data(**{"draft.children": [], "draft.bought_for_self": False, "step_mids": []})
        await context.set_state(RegistrationState.AWAITING_FIRST_NAME)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 1 из 4 · Как вас зовут? Введите имя или имя и отчество:",
            attachments=[cancel_keyboard("survey:cancel")],
        )
        await _append_step_mid(context, sent.message.mid)
        return

    if payload == "survey:resume":
        async with get_session_factory()() as session:
            cust = await customer_model.get_by_max_id(session, user_id)
        if not cust or not cust.survey_draft:
            await context.update_data(**{"draft.children": [], "draft.bought_for_self": False})
            await context.set_state(RegistrationState.AWAITING_FIRST_NAME)
            await _persist_survey_draft(context, user_id)
            await bot.send_message(
                user_id=user_id,
                text="Шаг 1 из 4 · Как вас зовут? Введите имя или имя и отчество:",
                attachments=[cancel_keyboard("survey:cancel")],
            )
            return
        draft = cust.survey_draft
        resume_state = draft.get("_state", RegistrationState.AWAITING_FIRST_NAME)
        restore_data = {k: v for k, v in draft.items() if k != "_state"}
        await context.update_data(**restore_data)
        await context.set_state(resume_state)
        data = await context.get_data()
        await _resend_survey_step(bot, user_id, resume_state, data, context)
        return

    if payload == "survey:restart":
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await customer_model.clear_survey_draft(session, user_id)
        except Exception:
            logger.warning("Failed to clear survey draft on restart for user %s", user_id)
        await context.update_data(**{
            "draft.first_name": None,
            "draft.last_name": None,
            "draft.birthdate": None,
            "draft.children": [],
            "draft.bought_for_self": False,
            "draft.phone": None,
            "step_mids": [],
        })
        await context.set_state(RegistrationState.AWAITING_FIRST_NAME)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 1 из 4 · Как вас зовут? Введите имя или имя и отчество:",
            attachments=[cancel_keyboard("survey:cancel")],
        )
        await _append_step_mid(context, sent.message.mid)
        return

    if payload == "survey:cancel" and state == RegistrationState.AWAITING_FIRST_NAME:
        await _delete_step_mids(bot, context)
        await context.update_data(**{"draft.first_name": None, "draft.children": [], "draft.bought_for_self": False})
        await context.set_state(RegistrationState.REGISTERED)
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await customer_model.clear_survey_draft(session, user_id)
        except Exception:
            logger.warning("Failed to clear survey draft on cancel for user %s", user_id)
        await bot.send_message(user_id=user_id, text="Главное меню.", attachments=[registered_keyboard()])
        return

    if payload == "survey:skip":
        data = await context.get_data()
        mid = data.get("survey_offer_mid")
        if mid:
            try:
                await bot.delete_message(message_id=mid)
            except Exception:
                pass
        return

    if payload == "skip":
        await _handle_survey_skip(bot, user_id, state, context)
        return

    if payload == "buy_for_self" and state == RegistrationState.AWAITING_CHILD_NAME:
        await context.update_data(**{"draft.bought_for_self": True})
        await context.set_state(RegistrationState.AWAITING_CONFIRMATION)
        await _persist_survey_draft(context, user_id)
        data = await context.get_data()
        await _send_confirmation_card(bot, user_id, data, context)
        return

    if payload == "back":
        await _handle_survey_back(bot, user_id, state, context)
        return

    if state == RegistrationState.AWAITING_CHILD_GENDER and payload.startswith("gender:"):
        gender = payload.split(":")[-1]
        data = await context.get_data()
        children = data.get("draft.children", [])
        if children:
            children[-1]["gender"] = gender
        await context.update_data(**{"draft.children": children})
        n = len(children)
        await context.set_state(RegistrationState.AWAITING_CHILD_BIRTHDATE)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 2 из 3 · Когда день рождения у ребёнка? "
                 "Будем поздравлять! 🎉 (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
        return

    if state == RegistrationState.AWAITING_MORE_CHILDREN and payload.startswith("more_children:"):
        if payload.endswith("yes"):
            data = await context.get_data()
            children = data.get("draft.children", [])
            await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
            await _persist_survey_draft(context, user_id)
            if not children:
                sent = await bot.send_message(
                    user_id=user_id,
                    text="Шаг 4 из 4 · Как зовут вашего ребёнка?",
                    attachments=[buy_for_self_keyboard()],
                )
            else:
                sent = await bot.send_message(
                    user_id=user_id,
                    text="Как зовут следующего ребёнка?",
                    attachments=[back_keyboard()],
                )
            await _append_step_mid(context, sent.message.mid)
        else:
            await context.set_state(RegistrationState.AWAITING_CONFIRMATION)
            await _persist_survey_draft(context, user_id)
            data = await context.get_data()
            await _send_confirmation_card(bot, user_id, data, context)
        return

    if state == RegistrationState.AWAITING_CONFIRMATION:
        if payload == "confirm:save":
            await context.set_state(RegistrationState.AWAITING_CONTACT)
            await _persist_survey_draft(context, user_id)
            sent = await bot.send_message(
                user_id=user_id,
                text=(
                    "Последний шаг — поделитесь контактом как запасным каналом связи. "
                    "Если что-то случится с ботом, мы не потеряем вас! Это необязательно."
                ),
                attachments=[contact_keyboard()],
            )
            await _append_step_mid(context, sent.message.mid)
        elif payload.startswith("edit:"):
            field = payload[5:]
            await context.update_data(**{"draft.editing_field": field})
            labels = {
                "first_name": "Имя",
                "last_name": "Фамилия",
                "birthdate": "Дата рождения (ДД.ММ.ГГГГ)",
            }
            label = labels.get(field, field)
            await bot.send_message(
                user_id=user_id,
                text=f"Введите новое значение — {label}:",
                attachments=[back_keyboard()],
            )
        return

    if state == RegistrationState.AWAITING_CONTACT and payload == "contact:skip":
        await _complete_survey(bot, user_id, context)
        return

    # Profile callbacks
    if payload == "profile:back":
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id, text="Главное меню.", attachments=[registered_keyboard()]
        )
        return

    if payload.startswith("profile:edit:"):
        field = payload[len("profile:edit:"):]
        cust = await get_customer()
        if cust is None:
            return
        await context.update_data(**{"edit.field": field})
        await context.set_state(ProfileState.EDITING_CUSTOMER_FIELD)
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "birthdate": "Дата рождения (ДД.ММ.ГГГГ)",
            "phone": "Телефон",
        }
        label = labels.get(field, field)
        current = getattr(cust, field, None) or "не указано"
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton
        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="Оставить текущее", payload="profile:keep_field"))
        if field != "first_name":
            builder.row(CallbackButton(text="Очистить поле", payload=f"profile:clear:{field}"))
        builder.row(CallbackButton(text="← Назад", payload="profile:edit_back"))
        await bot.send_message(
            user_id=user_id,
            text=f"Введите новое значение — {label}:\nТекущее: {current}",
            attachments=[builder.as_markup()],
        )
        return

    if payload == "profile:keep_field":
        cust = await get_customer()
        if cust is None:
            return
        await context.set_state(RegistrationState.REGISTERED)
        async with get_session_factory()() as session:
            ch = await child_model.get_by_customer(session, cust.id)
        await bot.send_message(
            user_id=user_id,
            text=_profile_text(cust, ch),
            attachments=[profile_card_keyboard(cust.opt_out_marketing)],
        )
        return

    if payload.startswith("profile:clear:"):
        field = payload[len("profile:clear:"):]
        cust = await get_customer()
        if cust is None:
            return
        async with get_session_factory()() as session:
            async with session.begin():
                cust = await customer_model.update_field(session, cust.id, **{field: None})
                ch = await child_model.get_by_customer(session, cust.id)
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text=_profile_text(cust, ch),
            attachments=[profile_card_keyboard(cust.opt_out_marketing)],
        )
        return

    if payload == "profile:edit_back":
        cust = await get_customer()
        if cust is None:
            return
        await context.set_state(RegistrationState.REGISTERED)
        async with get_session_factory()() as session:
            ch = await child_model.get_by_customer(session, cust.id)
        await bot.send_message(
            user_id=user_id,
            text=_profile_text(cust, ch),
            attachments=[profile_card_keyboard(cust.opt_out_marketing)],
        )
        return

    if payload in ("profile:opt_out", "profile:opt_in"):
        cust = await get_customer()
        if cust is None:
            return
        new_flag = payload == "profile:opt_out"
        async with get_session_factory()() as session:
            async with session.begin():
                cust = await customer_model.update_field(
                    session, cust.id, opt_out_marketing=new_flag
                )
                ch = await child_model.get_by_customer(session, cust.id)
        await bot.edit_message(
            message_id=event.message.body.mid,
            text=_profile_text(cust, ch),
            attachments=[profile_card_keyboard(cust.opt_out_marketing)],
        )
        return

    if payload == "profile:children":
        cust = await get_customer()
        if cust is None:
            return
        async with get_session_factory()() as session:
            children = await child_model.get_by_customer(session, cust.id)
        if children:
            await bot.send_message(
                user_id=user_id,
                text="👶 Ваши дети:",
                attachments=[children_list_keyboard(children)],
            )
        else:
            from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
            from maxapi.types import CallbackButton
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="➕ Добавить ребёнка", payload="child:add"))
            builder.row(CallbackButton(text="← Назад к профилю", payload="children:back"))
            await bot.send_message(
                user_id=user_id,
                text="У вас пока нет детей в профиле.",
                attachments=[builder.as_markup()],
            )
        return

    if payload == "children:back":
        cust = await get_customer()
        if cust is None:
            return
        async with get_session_factory()() as session:
            ch = await child_model.get_by_customer(session, cust.id)
        await bot.send_message(
            user_id=user_id,
            text=_profile_text(cust, ch),
            attachments=[profile_card_keyboard(cust.opt_out_marketing)],
        )
        return

    if payload.startswith("child:edit:") and "field" not in payload:
        child_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            ch = await child_model.get_by_id(session, child_id)
        if ch is None:
            await bot.send_message(user_id=user_id, text="Ребёнок не найден.")
            return
        await bot.send_message(
            user_id=user_id,
            text=_child_text(ch),
            attachments=[child_card_keyboard(child_id)],
        )
        return

    if payload.startswith("child:field:"):
        parts = payload.split(":")
        child_id = int(parts[2])
        child_field = parts[3]
        await context.update_data(**{"edit.child_id": child_id, "edit.child_field": child_field})
        await context.set_state("editing_child_field")
        if child_field == "gender":
            await bot.send_message(
                user_id=user_id, text="Выберите пол:", attachments=[gender_keyboard()]
            )
        else:
            labels = {"name": "Имя", "birthdate": "Дата рождения (ДД.ММ.ГГГГ)"}
            await bot.send_message(
                user_id=user_id,
                text=f"Введите новое значение — {labels.get(child_field, child_field)}:",
                attachments=[back_keyboard()],
            )
        return

    if payload.startswith("child:delete:"):
        child_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            ch = await child_model.get_by_id(session, child_id)
        name = ch.name if ch else str(child_id)
        await bot.send_message(
            user_id=user_id,
            text=f"Удалить {name} из профиля? Это действие нельзя отменить.",
            attachments=[confirm_delete_child_keyboard(child_id)],
        )
        return

    if payload.startswith("child:confirm_delete:"):
        child_id = int(payload.split(":")[-1])
        cust = await get_customer()
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await child_model.delete(session, child_id)
                    children = await child_model.get_by_customer(session, cust.id)
        except Exception:
            logger.exception("Child delete failed")
            await bot.send_message(user_id=user_id, text="Не удалось удалить.")
            return
        await bot.send_message(
            user_id=user_id,
            text="👶 Ваши дети:" if children else "У вас пока нет детей в профиле.",
            attachments=[children_list_keyboard(children)] if children else None,
        )
        return

    if payload == "child:back_to_list":
        cust = await get_customer()
        if cust is None:
            return
        async with get_session_factory()() as session:
            children = await child_model.get_by_customer(session, cust.id)
        await bot.send_message(
            user_id=user_id,
            text="👶 Ваши дети:" if children else "У вас пока нет детей в профиле.",
            attachments=[children_list_keyboard(children)] if children else None,
        )
        return

    if payload == "child:add":
        await context.set_state(ProfileState.ADDING_CHILD_NAME)
        await bot.send_message(
            user_id=user_id,
            text="Как зовут ребёнка?",
            attachments=[adding_child_back_keyboard()],
        )
        return

    if payload == "child:add_cancel":
        cust = await get_customer()
        if cust is None:
            return
        await context.set_state(RegistrationState.REGISTERED)
        async with get_session_factory()() as session:
            children = await child_model.get_by_customer(session, cust.id)
        await bot.send_message(
            user_id=user_id,
            text="👶 Ваши дети:" if children else "У вас пока нет детей в профиле.",
            attachments=[children_list_keyboard(children)] if children else None,
        )
        return

    if state == ProfileState.ADDING_CHILD_GENDER and payload.startswith("gender:"):
        gender = payload.split(":")[-1]
        await context.update_data(**{"new_child.gender": gender})
        await context.set_state(ProfileState.ADDING_CHILD_BIRTHDATE)
        await bot.send_message(
            user_id=user_id,
            text="Когда день рождения у ребёнка? (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard()],
        )
        return

    if state == ProfileState.ADDING_CHILD_BIRTHDATE and payload == "skip":
        cust = await get_customer()
        if cust is None:
            return
        data = await context.get_data()
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await child_model.create(
                        session,
                        customer_id=cust.id,
                        name=data["new_child.name"],
                        gender=data["new_child.gender"],
                        birthdate=None,
                    )
                    children = await child_model.get_by_customer(session, cust.id)
        except Exception:
            logger.exception("Add child (no birthdate) failed")
            await bot.send_message(user_id=user_id, text="Ошибка. Попробуйте ещё раз.")
            return
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text="👶 Ваши дети:",
            attachments=[children_list_keyboard(children)],
        )
        return

    if state in (ProfileState.ADDING_CHILD_GENDER, ProfileState.ADDING_CHILD_BIRTHDATE) and payload == "back":
        if state == ProfileState.ADDING_CHILD_BIRTHDATE:
            await context.set_state(ProfileState.ADDING_CHILD_GENDER)
            await bot.send_message(
                user_id=user_id,
                text="Ваш ребёнок — мальчик или девочка?",
                attachments=[gender_keyboard()],
            )
        else:
            await context.set_state(ProfileState.ADDING_CHILD_NAME)
            await bot.send_message(
                user_id=user_id,
                text="Как зовут ребёнка?",
                attachments=[adding_child_back_keyboard()],
            )
        return

    if state == "editing_child_field" and payload.startswith("gender:"):
        data = await context.get_data()
        child_id = data.get("edit.child_id")
        gender = payload.split(":")[-1]
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    updated = await child_model.update_field(session, child_id, gender=gender)
        except Exception:
            logger.exception("Child gender update failed")
            return
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text=_child_text(updated),
            attachments=[child_card_keyboard(child_id)],
        )
        return


async def _persist_survey_draft(context, user_id: int) -> None:
    data = await context.get_data()
    state = await context.get_state()
    draft = {k: v for k, v in data.items() if k.startswith("draft.") or k == "survey_offer_mid"}
    draft["_state"] = str(state)
    try:
        async with get_session_factory()() as session:
            async with session.begin():
                await customer_model.save_survey_draft(session, user_id, draft)
    except Exception:
        logger.warning("Failed to persist survey draft for user %s", user_id)


def _format_resume_message(draft: dict) -> str:
    fn = draft.get("draft.first_name")
    ln = draft.get("draft.last_name")
    bd = draft.get("draft.birthdate")
    children = draft.get("draft.children", [])

    lines = ["👋 Вы уже начали заполнять анкету!\n"]
    if fn:
        lines.append(f"✅ Имя: {fn}")
    if ln:
        lines.append(f"✅ Фамилия: {ln}")
    if bd:
        lines.append(f"✅ Дата рождения: {bd}")
    if children:
        names = ", ".join(ch["name"] for ch in children if ch.get("name"))
        lines.append(f"✅ Дети: {names}")

    remaining = []
    if not bd:
        remaining.append("дата рождения")
    if not children:
        remaining.append("данные детей")
    if remaining:
        lines.append(f"\n⏳ Осталось: {', '.join(remaining)}")

    return "\n".join(lines)


async def _resend_survey_step(bot, user_id: int, state: str, data: dict, context: MemoryContext) -> None:
    children = data.get("draft.children", [])
    n = len(children)

    if state == RegistrationState.AWAITING_FIRST_NAME:
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 1 из 4 · Как вас зовут? Введите имя или имя и отчество:",
            attachments=[cancel_keyboard("survey:cancel")],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_LAST_NAME:
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 2 из 4 · Расскажите свою фамилию — поможет при официальном обращении. "
                 "Можно пропустить 😊",
            attachments=[back_and_skip_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 3 из 4 · Когда ваш день рождения? Обязательно поздравим! 🎂 (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CHILD_NAME:
        if not children:
            sent = await bot.send_message(
                user_id=user_id,
                text="Шаг 4 из 4 · Как зовут вашего ребёнка?",
                attachments=[buy_for_self_keyboard()],
            )
        else:
            sent = await bot.send_message(
                user_id=user_id,
                text="Как зовут следующего ребёнка?",
                attachments=[back_keyboard()],
            )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CHILD_GENDER:
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 1 из 3 · Ваш ребёнок — мальчик или девочка? "
                 "Подберём подходящие предложения:",
            attachments=[gender_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 2 из 3 · Когда день рождения у ребёнка? "
                 "Будем поздравлять! 🎉 (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_MORE_CHILDREN:
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 3 из 3 · Хотите добавить ещё одного ребёнка?",
            attachments=[yes_no_keyboard("more_children:yes", "more_children:no")],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CONFIRMATION:
        await _send_confirmation_card(bot, user_id, data, context)
    elif state == RegistrationState.AWAITING_CONTACT:
        sent = await bot.send_message(
            user_id=user_id,
            text=(
                "Последний шаг — поделитесь контактом как запасным каналом связи. "
                "Если что-то случится с ботом, мы не потеряем вас! Это необязательно."
            ),
            attachments=[contact_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)


async def _send_confirmation_card(bot, user_id, data, context: MemoryContext):
    children = data.get("draft.children", [])
    text = _format_confirmation(data)
    sent = await bot.send_message(
        user_id=user_id,
        text=text,
        attachments=[confirmation_card_keyboard(has_children=bool(children))],
    )
    await _append_step_mid(context, sent.message.mid)
    await context.update_data(confirmation_card_mid=sent.message.mid)


async def _handle_survey_skip(bot, user_id, state, context):
    if state == RegistrationState.AWAITING_LAST_NAME:
        await context.update_data(**{"draft.last_name": None})
        await context.set_state(RegistrationState.AWAITING_CUSTOMER_BIRTHDATE)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 3 из 4 · Когда ваш день рождения? Обязательно поздравим! 🎂 (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        await context.update_data(**{"draft.birthdate": None})
        data = await context.get_data()
        children = data.get("draft.children", [])
        await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
        await _persist_survey_draft(context, user_id)
        if not children:
            sent = await bot.send_message(
                user_id=user_id,
                text="Шаг 4 из 4 · Как зовут вашего ребёнка?",
                attachments=[buy_for_self_keyboard()],
            )
        else:
            sent = await bot.send_message(
                user_id=user_id,
                text="Как зовут следующего ребёнка?",
                attachments=[back_keyboard()],
            )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        data = await context.get_data()
        children = data.get("draft.children", [])
        if children:
            children[-1]["birthdate"] = None
        await context.update_data(**{"draft.children": children})
        n = len(children)
        await context.set_state(RegistrationState.AWAITING_MORE_CHILDREN)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 3 из 3 · Хотите добавить ещё одного ребёнка?",
            attachments=[yes_no_keyboard("more_children:yes", "more_children:no")],
        )
        await _append_step_mid(context, sent.message.mid)


async def _handle_survey_back(bot, user_id, state, context):
    data = await context.get_data()

    if state == RegistrationState.AWAITING_LAST_NAME:
        await context.set_state(RegistrationState.AWAITING_FIRST_NAME)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 1 из 4 · Как вас зовут? Введите имя или имя и отчество:",
            attachments=[cancel_keyboard("survey:cancel")],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        await context.set_state(RegistrationState.AWAITING_LAST_NAME)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 2 из 4 · Расскажите свою фамилию. Можно пропустить 😊",
            attachments=[back_and_skip_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CHILD_NAME:
        children = data.get("draft.children", [])
        if children:
            await context.set_state(RegistrationState.AWAITING_MORE_CHILDREN)
            await _persist_survey_draft(context, user_id)
            sent = await bot.send_message(
                user_id=user_id,
                text="Хотите добавить ещё одного ребёнка?",
                attachments=[yes_no_keyboard("more_children:yes", "more_children:no")],
            )
        else:
            await context.set_state(RegistrationState.AWAITING_CUSTOMER_BIRTHDATE)
            await _persist_survey_draft(context, user_id)
            sent = await bot.send_message(
                user_id=user_id,
                text="Шаг 3 из 4 · Когда ваш день рождения? 🎂 (ДД.ММ.ГГГГ)",
                attachments=[back_and_skip_keyboard()],
            )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CHILD_GENDER:
        children = data.get("draft.children", [])
        if children:
            children.pop()
        await context.update_data(**{"draft.children": children})
        await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
        await _persist_survey_draft(context, user_id)
        children_remaining = len(children)
        if children_remaining == 0:
            sent = await bot.send_message(
                user_id=user_id,
                text="Шаг 4 из 4 · Как зовут вашего ребёнка?",
                attachments=[buy_for_self_keyboard()],
            )
        else:
            sent = await bot.send_message(
                user_id=user_id,
                text="Как зовут следующего ребёнка?",
                attachments=[back_keyboard()],
            )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        await context.set_state(RegistrationState.AWAITING_CHILD_GENDER)
        await _persist_survey_draft(context, user_id)
        children = data.get("draft.children", [])
        n = len(children)
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 1 из 3 · Ваш ребёнок — мальчик или девочка?",
            attachments=[gender_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_MORE_CHILDREN:
        await context.set_state(RegistrationState.AWAITING_CHILD_BIRTHDATE)
        await _persist_survey_draft(context, user_id)
        children = data.get("draft.children", [])
        n = len(children)
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 2 из 3 · Когда день рождения у ребёнка? (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard()],
        )
        await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CONFIRMATION:
        children = data.get("draft.children", [])
        if children:
            await context.set_state(RegistrationState.AWAITING_MORE_CHILDREN)
            await _persist_survey_draft(context, user_id)
            sent = await bot.send_message(
                user_id=user_id,
                text="Хотите добавить ещё одного ребёнка?",
                attachments=[yes_no_keyboard("more_children:yes", "more_children:no")],
            )
            await _append_step_mid(context, sent.message.mid)
        else:
            await context.set_state(RegistrationState.AWAITING_CUSTOMER_BIRTHDATE)
            await _persist_survey_draft(context, user_id)
            sent = await bot.send_message(
                user_id=user_id,
                text="Шаг 3 из 4 · Когда ваш день рождения? 🎂 (ДД.ММ.ГГГГ)",
                attachments=[back_and_skip_keyboard()],
            )
            await _append_step_mid(context, sent.message.mid)
    elif state == RegistrationState.AWAITING_CONTACT:
        await context.set_state(RegistrationState.AWAITING_CONFIRMATION)
        await _persist_survey_draft(context, user_id)
        data = await context.get_data()
        await _send_confirmation_card(bot, user_id, data, context)


async def _complete_survey(bot, user_id, context):
    from src.models import child as child_model_mod
    data = await context.get_data()
    children_draft = data.get("draft.children", [])
    survey_completed = True

    first_name = data.get("draft.first_name") or ""
    last_name = data.get("draft.last_name")
    bd_str = data.get("draft.birthdate")
    birthdate = date.fromisoformat(bd_str) if bd_str else None
    phone = data.get("draft.phone")

    try:
        async with get_session_factory()() as session:
            async with session.begin():
                cust = await customer_model.get_by_max_id(session, user_id)
                was_completed = cust.survey_completed if cust else False
                cust = await customer_model.update_survey_data(
                    session,
                    max_user_id=user_id,
                    first_name=first_name,
                    last_name=last_name,
                    birthdate=birthdate,
                    phone=phone,
                    survey_completed=survey_completed,
                )
                for ch_data in children_draft:
                    bd = (
                        date.fromisoformat(ch_data["birthdate"])
                        if ch_data.get("birthdate")
                        else None
                    )
                    await child_model_mod.create(
                        session,
                        customer_id=cust.id,
                        name=ch_data["name"],
                        gender=ch_data["gender"],
                        birthdate=bd,
                    )
                survey_coupon = None
                if not was_completed and survey_completed:
                    survey_coupon = await coupon_model.create_survey_coupon(session, cust.id)
                await customer_model.clear_survey_draft(session, user_id)
        logger.info("Survey saved for max_user_id=%s survey_completed=%s", user_id, survey_completed)
    except Exception:
        logger.exception("Survey save failed for max_user_id=%s", user_id)
        await bot.send_message(
            user_id=user_id, text="Ошибка при сохранении. Попробуйте ещё раз."
        )
        return

    await context.set_state(RegistrationState.REGISTERED)
    await _delete_step_mids(bot, context)
    await bot.send_message(
        user_id=user_id,
        text="Анкета заполнена! Спасибо 🎉",
        attachments=[registered_keyboard()],
    )
    if survey_coupon is not None:
        try:
            await bot.send_message(
                user_id=user_id,
                text=coupon_issued_notification(survey_coupon),
            )
        except Exception:
            logger.warning("Could not send coupon notification to user %s", user_id)
