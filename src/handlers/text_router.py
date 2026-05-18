"""
Single unified handler for all F.message.body.text events.
Routes to sub-handlers based on `route` (from middleware) and FSM state.
This avoids multiple handlers competing for the same event type.
"""
import logging
from datetime import date, datetime, timezone

from maxapi.types import MessageCreated
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import RegistrationState, ProfileState, StaffState
from src.db.orm import Customer, Staff
from maxapi.enums.parse_mode import ParseMode as TextFormat
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model
from src.models import coupon as coupon_model
from src.models import staff as staff_model
from src.models import broadcast as broadcast_model
from src.keyboards import (
    registered_keyboard,
    unregistered_keyboard,
    staff_keyboard,
    superuser_keyboard,
    back_keyboard,
    back_and_skip_keyboard,
    gender_keyboard,
    buy_for_self_keyboard,
    yes_no_keyboard,
    confirmation_card_keyboard,
    profile_card_keyboard,
    children_list_keyboard,
    cancel_keyboard,
    broadcast_start_keyboard,
)
import config
from src.handlers.registration import _format_confirmation, _parse_date, _parse_int_list
from src.handlers.profile import _profile_text, _child_text
from src.handlers.broadcast import _parse_scheduled_at, _create_broadcast, _in_window, _ask_broadcast_recipients
from src.handlers.staff import _send_customer_profile_by_id
from src.handlers.callbacks._common import _persist_survey_draft, _append_step_mid, _delete_step_mids
from src.services.discount import coupon_issued_notification

logger = logging.getLogger(__name__)


async def register_text_router(dp):

    @dp.message_created(F.message.body.text)
    async def unified_text_handler(
        event: MessageCreated,
        context: MemoryContext,
        route: str = "registration",
        customer: Customer | None = None,
        staff: Staff | None = None,
    ):
        text = event.message.body.text.strip()
        user_id = event.message.sender.user_id
        state = await context.get_state()

        # --- Staff routes ---
        if route == "staff" and staff is not None:
            await _handle_staff_text(event, context, staff, state, text, user_id)
            return

        # --- Customer / registration routes ---
        await _handle_customer_text(event, context, customer, state, text, user_id, route)


async def _handle_staff_text(event, context, staff, state, text, user_id):
    bot = event.bot

    # Broadcast states (owner only)
    if staff.is_owner:
        if state == StaffState.AWAITING_BROADCAST_MSG:
            from src.handlers.broadcast import _save_broadcast_source
            await _save_broadcast_source(event, context)
            return

        if state == StaffState.AWAITING_BROADCAST_RECIPIENTS:
            ids = list(dict.fromkeys(_parse_int_list(text)))
            if not ids:
                sent = await bot.send_message(
                    user_id=user_id,
                    text=(
                        "Не удалось разобрать список ID. Попробуйте ещё раз.\n"
                        "Шаг 3 из 4 · Пришлите номера клиентов (через запятую или с новой строки):"
                    ),
                    attachments=[cancel_keyboard("broadcast:cancel_create")],
                )
                await _append_step_mid(context, sent.message.body.mid)
                return
            async with get_session_factory()() as session:
                eligible = await broadcast_model.get_eligible_customer_ids(session, ids)
            await context.update_data(broadcast_recipient_ids=eligible)
            await context.set_state(StaffState.AWAITING_BROADCAST_TIME)
            sent = await bot.send_message(
                user_id=user_id,
                text=(
                    f"Шаг 4 из 4 · Создана рассылка на {len(eligible)} получателей. Когда её начать?\n"
                    f"Рассылку можно запланировать с {config.BROADCAST_WINDOW_START_HOUR}:00 "
                    f"до {config.BROADCAST_WINDOW_END_HOUR}:00.\n"
                    "Укажите дату:\n"
                    f"  • «25.06» — 25 июня в {config.BROADCAST_WINDOW_START_HOUR}:00\n"
                    "  • «25.06 14:30» — 25 июня в 14:30"
                ),
                attachments=[broadcast_start_keyboard()],
            )
            await _append_step_mid(context, sent.message.body.mid)
            return

        if state == StaffState.AWAITING_BROADCAST_TIME:
            scheduled_at = _parse_scheduled_at(text)
            if scheduled_at is None:
                sent = await bot.send_message(
                    user_id=user_id,
                    text=(
                        "Шаг 4 из 4 · Не понял дату. Укажите в формате «ДД.ММ» или «ДД.ММ ЧЧ:ММ»:\n"
                        f"  • «25.06» — 25 июня в {config.BROADCAST_WINDOW_START_HOUR}:00\n"
                        "  • «25.06 14:30» — 25 июня в 14:30"
                    ),
                    attachments=[broadcast_start_keyboard()],
                )
                await _append_step_mid(context, sent.message.body.mid)
                return
            if not _in_window(scheduled_at):
                sent = await bot.send_message(
                    user_id=user_id,
                    text=(
                        f"Шаг 4 из 4 · Время {scheduled_at.strftime('%H:%M')} недоступно. "
                        f"Укажите с {config.BROADCAST_WINDOW_START_HOUR}:00 "
                        f"до {config.BROADCAST_WINDOW_END_HOUR}:00:"
                    ),
                    attachments=[broadcast_start_keyboard()],
                )
                await _append_step_mid(context, sent.message.body.mid)
                return
            await _create_broadcast(bot, user_id, context, scheduled_at)
            return

    # Scenario 15 Flow B: coupon issuance
    if state == StaffState.AWAITING_COUPON_VALUE:
        try:
            val = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id,
                text="Введите целое число.",
                attachments=[cancel_keyboard("coupon:issue_cancel")],
            )
            return
        if val < 101 or val > 1000:
            await bot.send_message(
                user_id=user_id,
                text="Введите сумму от 101 до 1000 рублей.",
                attachments=[cancel_keyboard("coupon:issue_cancel")],
            )
            return
        data = await context.get_data()
        coupon_ctx = data.get("coupon_context", "seller")
        await context.update_data(coupon_draft_value=val)
        await context.set_state(StaffState.AWAITING_COUPON_DAYS)
        sent = await bot.send_message(
            user_id=user_id,
            text="Срок действия купона (в днях, минимум 7):",
            attachments=[cancel_keyboard("coupon:issue_cancel")],
        )
        if coupon_ctx == "broadcast":
            await _append_step_mid(context, sent.message.body.mid)
        return

    if state == StaffState.AWAITING_COUPON_DAYS:
        try:
            days = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id,
                text="Введите целое число.",
                attachments=[cancel_keyboard("coupon:issue_cancel")],
            )
            return
        if days < 7:
            await bot.send_message(
                user_id=user_id,
                text="Срок должен быть не менее 7 дней.",
                attachments=[cancel_keyboard("coupon:issue_cancel")],
            )
            return
        data = await context.get_data()
        coupon_ctx = data.get("coupon_context", "seller")
        await context.update_data(coupon_draft_days=days)
        await context.set_state(StaffState.AWAITING_COUPON_PCT)
        sent = await bot.send_message(
            user_id=user_id,
            text="Введите % суммы покупки, которые можно оплатить купоном (до 30%):",
            attachments=[cancel_keyboard("coupon:issue_cancel")],
        )
        if coupon_ctx == "broadcast":
            await _append_step_mid(context, sent.message.body.mid)
        return

    if state == StaffState.AWAITING_COUPON_PCT:
        try:
            pct = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id,
                text="Введите целое число.",
                attachments=[cancel_keyboard("coupon:issue_cancel")],
            )
            return
        if pct < 1 or pct > 30:
            await bot.send_message(
                user_id=user_id,
                text="Введите процент от 1 до 30.",
                attachments=[cancel_keyboard("coupon:issue_cancel")],
            )
            return
        data = await context.get_data()
        coupon_ctx = data.get("coupon_context", "seller")

        if coupon_ctx == "broadcast":
            await context.update_data(
                broadcast_coupon_value=data.get("coupon_draft_value"),
                broadcast_coupon_days=data.get("coupon_draft_days"),
                broadcast_coupon_pct=pct,
                coupon_context=None,
            )
            await _ask_broadcast_recipients(bot, user_id, context)
            return

        customer_id = data.get("coupon_target_customer_id")
        value = data.get("coupon_draft_value")
        days = data.get("coupon_draft_days")
        survey_coupon = None
        cust = None
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    survey_coupon = await coupon_model.create_seller_coupon(
                        session, customer_id, value, days, pct
                    )
                    cust = await customer_model.get_by_id(session, customer_id)
        except Exception:
            logger.exception("Seller coupon creation failed for customer_id=%s", customer_id)
            await bot.send_message(user_id=user_id, text="Ошибка. Попробуйте ещё раз.")
            return
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(user_id=user_id, text="Купон выдан.")
        if cust:
            try:
                await bot.send_message(
                    user_id=cust.max_user_id,
                    text=coupon_issued_notification(survey_coupon),
                )
            except Exception:
                logger.warning("Could not notify customer %s of coupon issuance", cust.max_user_id)
        await _send_customer_profile_by_id(bot, user_id, customer_id)
        return

    # Customer ID lookup
    if state == StaffState.AWAITING_CUSTOMER_ID:
        try:
            customer_id = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id,
                text="Введите числовой номер клиента.",
                attachments=[cancel_keyboard("find_customer:cancel")],
            )
            return
        await context.set_state(RegistrationState.REGISTERED)
        await _send_customer_profile_by_id(bot, user_id, customer_id)
        return

    # Discount value input
    if state == StaffState.AWAITING_DISCOUNT_VALUE:
        data = await context.get_data()
        customer_id = data.get("editing_customer_id")
        customer_max_id = data.get("editing_customer_max_id")
        if customer_id is None:
            await context.set_state(RegistrationState.REGISTERED)
            return
        try:
            val = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id,
                text="Введите число от 0 до 30.",
                attachments=[cancel_keyboard("discount:cancel")],
            )
            return
        if val < 0 or val > 30:
            await bot.send_message(
                user_id=user_id,
                text="Введите число от 0 до 30.",
                attachments=[cancel_keyboard("discount:cancel")],
            )
            return
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    old = await customer_model.get_by_id(session, customer_id)
                    old_pct = old.discount_percent if old else "?"
                    await customer_model.set_discount(session, customer_id, val)
        except Exception:
            logger.exception("Discount update failed for customer_id=%s", customer_id)
            await bot.send_message(user_id=user_id, text="Ошибка при изменении скидки. Попробуйте ещё раз.")
            return
        await bot.send_message(
            user_id=user_id,
            text=f"Скидка изменена: <s>{old_pct}%</s> → {val}%",
            parse_mode=TextFormat.HTML,
        )
        if customer_max_id:
            try:
                await bot.send_message(
                    user_id=customer_max_id,
                    text=f"Ваша скидка изменена: <s>{old_pct}%</s> → {val}%",
                    parse_mode=TextFormat.HTML,
                )
            except Exception:
                logger.warning("Could not notify customer %s of discount change", customer_max_id)
        await context.set_state(RegistrationState.REGISTERED)
        await _send_customer_profile_by_id(bot, user_id, customer_id)
        return

    # Fallback: unrecognised message in idle state
    if state in (RegistrationState.REGISTERED, None):
        kb = superuser_keyboard() if staff.is_owner else staff_keyboard()
        await bot.send_message(
            user_id=user_id,
            text="Извините, я глупый бот и вас не понял, но вы можете явно выбрать одно из следующих действий.",
            attachments=[kb],
        )


async def _handle_customer_text(event, context, customer, state, text, user_id, route="customer"):
    bot = event.bot

    # Survey states
    if state == RegistrationState.AWAITING_FIRST_NAME:
        await context.update_data(**{"draft.first_name": text})
        await context.set_state(RegistrationState.AWAITING_LAST_NAME)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 2 из 4 · Расскажите свою фамилию — поможет при официальном обращении. "
                 "Можно пропустить 😊",
            attachments=[back_and_skip_keyboard("survey:cancel")],
        )
        await _append_step_mid(context, sent.message.body.mid)
        return

    if state == RegistrationState.AWAITING_LAST_NAME:
        await context.update_data(**{"draft.last_name": text})
        await context.set_state(RegistrationState.AWAITING_CUSTOMER_BIRTHDATE)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text="Шаг 3 из 4 · Когда ваш день рождения? Обязательно поздравим! 🎂 (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard("survey:cancel")],
        )
        await _append_step_mid(context, sent.message.body.mid)
        return

    if state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        bd = _parse_date(text)
        if bd is None:
            sent = await bot.send_message(
                user_id=user_id,
                text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                attachments=[back_and_skip_keyboard("survey:cancel")],
            )
            await _append_step_mid(context, sent.message.body.mid)
            return
        await context.update_data(**{"draft.birthdate": str(bd)})
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
                text=f"Ребёнок {len(children) + 1} · шаг 1 из 3 · Как зовут ребёнка?",
                attachments=[back_keyboard()],
            )
        await _append_step_mid(context, sent.message.body.mid)
        return

    if state == RegistrationState.AWAITING_CHILD_NAME:
        data = await context.get_data()
        children = data.get("draft.children", [])
        children.append({"name": text, "gender": None, "birthdate": None})
        await context.update_data(**{"draft.children": children})
        n = len(children)
        await context.set_state(RegistrationState.AWAITING_CHILD_GENDER)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 1 из 3 · Ваш ребёнок — мальчик или девочка? "
                 "Подберём подходящие предложения:",
            attachments=[gender_keyboard()],
        )
        await _append_step_mid(context, sent.message.body.mid)
        return

    if state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        bd = _parse_date(text)
        if bd is None:
            sent = await bot.send_message(
                user_id=user_id,
                text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                attachments=[back_and_skip_keyboard("survey:cancel")],
            )
            await _append_step_mid(context, sent.message.body.mid)
            return
        data = await context.get_data()
        children = data.get("draft.children", [])
        if children:
            children[-1]["birthdate"] = str(bd)
        await context.update_data(**{"draft.children": children})
        n = len(children)
        await context.set_state(RegistrationState.AWAITING_MORE_CHILDREN)
        await _persist_survey_draft(context, user_id)
        sent = await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 3 из 3 · Хотите добавить ещё одного ребёнка?",
            attachments=[yes_no_keyboard("more_children:yes", "more_children:no")],
        )
        await _append_step_mid(context, sent.message.body.mid)
        return

    # Survey confirmation card inline edit
    if state == RegistrationState.AWAITING_CONFIRMATION:
        data = await context.get_data()
        field = data.get("draft.editing_field")
        if field:
            if field == "birthdate":
                val = _parse_date(text)
                if val is None:
                    sent = await bot.send_message(
                        user_id=user_id,
                        text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                        attachments=[back_keyboard()],
                    )
                    await _append_step_mid(context, sent.message.body.mid)
                    return
                val = str(val)
            else:
                val = text
            await context.update_data(**{f"draft.{field}": val, "draft.editing_field": None})
            await _persist_survey_draft(context, user_id)
            data = await context.get_data()
            children = data.get("draft.children", [])
            card_mid = data.get("confirmation_card_mid")
            if card_mid:
                try:
                    await bot.edit_message(
                        message_id=card_mid,
                        text=_format_confirmation(data),
                        attachments=[confirmation_card_keyboard(has_children=bool(children))],
                    )
                except Exception:
                    logger.warning("edit_message failed for confirmation card, sending new")
                    await bot.send_message(
                        user_id=user_id,
                        text=_format_confirmation(data),
                        attachments=[confirmation_card_keyboard(has_children=bool(children))],
                    )
            else:
                await bot.send_message(
                    user_id=user_id,
                    text=_format_confirmation(data),
                    attachments=[confirmation_card_keyboard(has_children=bool(children))],
                )
        return

    # Profile editing states
    if state == ProfileState.EDITING_CUSTOMER_FIELD:
        if customer is None:
            async with get_session_factory()() as session:
                customer = await customer_model.get_by_max_id(session, user_id)
        if customer is None:
            return
        data = await context.get_data()
        field = data.get("edit.field")
        if field == "birthdate":
            val = _parse_date(text)
            if val is None:
                await bot.send_message(
                    user_id=user_id,
                    text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                    attachments=[back_keyboard()],
                )
                return
        else:
            val = text
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    c = await customer_model.update_field(session, customer.id, **{field: val})
                    ch = await child_model.get_by_customer(session, customer.id)
        except Exception:
            logger.exception("Profile field update failed")
            await bot.send_message(
                user_id=user_id, text="Не удалось сохранить изменение. Попробуйте ещё раз."
            )
            return
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text=_profile_text(c, ch),
            attachments=[profile_card_keyboard(c.opt_out_marketing)],
        )
        return

    if state == ProfileState.ADDING_CHILD_NAME:
        await context.update_data(**{"new_child.name": text})
        await context.set_state(ProfileState.ADDING_CHILD_GENDER)
        sent = await bot.send_message(
            user_id=user_id,
            text="Ваш ребёнок — мальчик или девочка?",
            attachments=[gender_keyboard()],
        )
        await _append_step_mid(context, sent.message.body.mid)
        return

    if state == ProfileState.ADDING_CHILD_BIRTHDATE:
        bd = _parse_date(text)
        if bd is None:
            await bot.send_message(
                user_id=user_id,
                text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                attachments=[back_and_skip_keyboard()],
            )
            return
        if customer is None:
            async with get_session_factory()() as session:
                customer = await customer_model.get_by_max_id(session, user_id)
        if customer is None:
            return
        data = await context.get_data()
        new_survey_coupon = None
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await child_model.create(
                        session,
                        customer_id=customer.id,
                        name=data["new_child.name"],
                        gender=data["new_child.gender"],
                        birthdate=bd,
                    )
                    if not customer.survey_completed and bd is not None:
                        await customer_model.update_field(
                            session, customer.id, survey_completed=True
                        )
                        new_survey_coupon = await coupon_model.create_survey_coupon(session, customer.id)
                    children = await child_model.get_by_customer(session, customer.id)
        except Exception:
            logger.exception("Add child failed")
            await bot.send_message(user_id=user_id, text="Не удалось сохранить. Попробуйте ещё раз.")
            return
        await context.set_state(RegistrationState.REGISTERED)
        await _delete_step_mids(bot, context)
        await bot.send_message(
            user_id=user_id,
            text="👶 Ваши дети:",
            attachments=[children_list_keyboard(children)],
        )
        if new_survey_coupon is not None:
            try:
                await bot.send_message(
                    user_id=user_id,
                    text=coupon_issued_notification(new_survey_coupon),
                )
            except Exception:
                logger.warning("Could not send coupon notification to user %s", user_id)
        return

    if state == "editing_child_field":
        if customer is None:
            async with get_session_factory()() as session:
                customer = await customer_model.get_by_max_id(session, user_id)
        if customer is None:
            return
        data = await context.get_data()
        child_id = data.get("edit.child_id")
        child_field = data.get("edit.child_field")
        if child_field == "birthdate":
            val = _parse_date(text)
            if val is None:
                await bot.send_message(
                    user_id=user_id,
                    text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                    attachments=[back_keyboard()],
                )
                return
        else:
            val = text
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    updated = await child_model.update_field(session, child_id, **{child_field: val})
        except Exception:
            logger.exception("Child field update failed")
            await bot.send_message(user_id=user_id, text="Не удалось сохранить. Попробуйте ещё раз.")
            return
        from src.keyboards import child_card_keyboard
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text=_child_text(updated),
            attachments=[child_card_keyboard(child_id)],
        )
        return

    # Fallback: unrecognised message in idle state
    if state in (RegistrationState.REGISTERED, None):
        kb = unregistered_keyboard() if route == "registration" else registered_keyboard()
        await bot.send_message(
            user_id=user_id,
            text="Извините, я глупый бот и вас не понял, но вы можете явно выбрать одно из следующих действий.",
            attachments=[kb],
        )
