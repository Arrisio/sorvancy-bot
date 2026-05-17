"""
Single unified handler for all F.message.body.text events.
Routes to sub-handlers based on `route` (from middleware) and FSM state.
This avoids multiple handlers competing for the same event type.
"""
import re
import logging
from datetime import date, datetime, timezone

from maxapi.types import MessageCreated
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import RegistrationState, ProfileState, StaffState
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model
from src.models import coupon as coupon_model
from src.models import staff as staff_model
from src.models import broadcast as broadcast_model
from src.keyboards import (
    registered_keyboard,
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
from src.handlers.registration import _format_confirmation, _parse_date
from src.handlers.profile import _profile_text, _child_text
from src.handlers.broadcast import _parse_scheduled_at, _create_broadcast
from src.handlers.staff import _send_customer_profile_by_id

logger = logging.getLogger(__name__)


async def register_text_router(dp):

    @dp.message_created(F.message.body.text)
    async def unified_text_handler(
        event: MessageCreated,
        context: MemoryContext,
        route: str = "registration",
        customer=None,
        staff=None,
    ):
        text = event.message.body.text.strip()
        user_id = event.message.sender.user_id
        state = await context.get_state()

        # --- Staff routes ---
        if route == "staff" and staff is not None:
            await _handle_staff_text(event, context, staff, state, text, user_id)
            return

        # --- Customer / registration routes ---
        await _handle_customer_text(event, context, customer, state, text, user_id)


async def _handle_staff_text(event, context, staff, state, text, user_id):
    bot = event.bot

    # Broadcast states (owner only)
    if staff.is_owner:
        if state == StaffState.AWAITING_BROADCAST_MSG:
            mid = event.message.mid
            chat_id = None
            try:
                chat_id = event.message.recipient.chat_id
            except Exception:
                chat_id = user_id
            await context.update_data(
                broadcast_source_mid=mid,
                broadcast_source_chat_id=chat_id,
            )
            await context.set_state(StaffState.AWAITING_BROADCAST_RECIPIENTS)
            await bot.send_message(
                user_id=user_id,
                text="Пришлите номера клиентов для рассылки (через запятую или с новой строки):",
                attachments=[cancel_keyboard("broadcast:cancel_create")],
            )
            return

        if state == StaffState.AWAITING_BROADCAST_RECIPIENTS:
            raw_ids = re.split(r"[\s,;]+", text)
            ids = [int(r) for r in raw_ids if r.strip().isdigit()]
            if not ids:
                await bot.send_message(
                    user_id=user_id,
                    text="Не удалось разобрать список ID. Попробуйте ещё раз."
                )
                return
            async with get_session_factory()() as session:
                eligible = await broadcast_model.get_eligible_customer_ids(session, ids)
            await context.update_data(broadcast_recipient_ids=eligible)
            await context.set_state(StaffState.AWAITING_BROADCAST_TIME)
            await bot.send_message(
                user_id=user_id,
                text=f"Создана рассылка на {len(eligible)} получателей. Когда её начать?",
                attachments=[broadcast_start_keyboard()],
            )
            return

        if state == StaffState.AWAITING_BROADCAST_TIME:
            scheduled_at = _parse_scheduled_at(text)
            if scheduled_at is None:
                await bot.send_message(
                    user_id=user_id,
                    text="Не понял дату. Укажите в формате «ДД.ММ» или «ДД.ММ ЧЧ:ММ»"
                )
                return
            await _create_broadcast(bot, user_id, context, scheduled_at, status="pending")
            return

    # Customer ID lookup
    if state == StaffState.AWAITING_CUSTOMER_ID:
        try:
            customer_id = int(text)
        except ValueError:
            await bot.send_message(user_id=user_id, text="Введите числовой номер клиента.")
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
            await bot.send_message(user_id=user_id, text="Введите число от 0 до 30.")
            return
        if val < 0 or val > 30:
            await bot.send_message(user_id=user_id, text="Введите число от 0 до 30.")
            return
        async with get_session_factory()() as session:
            async with session.begin():
                old = await customer_model.get_by_id(session, customer_id)
                old_pct = old.discount_percent if old else "?"
                await customer_model.set_discount(session, customer_id, val)
        await bot.send_message(user_id=user_id, text=f"Скидка изменена: {old_pct}% → {val}%")
        if customer_max_id:
            try:
                await bot.send_message(
                    user_id=customer_max_id,
                    text=f"Ваша скидка изменена: {old_pct}% → {val}%",
                )
            except Exception:
                logger.warning("Could not notify customer %s of discount change", customer_max_id)
        await context.set_state(RegistrationState.REGISTERED)
        return


async def _handle_customer_text(event, context, customer, state, text, user_id):
    bot = event.bot

    # Survey states
    if state == RegistrationState.AWAITING_FIRST_NAME:
        await context.update_data(**{"draft.first_name": text})
        await context.set_state(RegistrationState.AWAITING_LAST_NAME)
        await bot.send_message(
            user_id=user_id,
            text="Шаг 2 из 4 · Расскажите свою фамилию — поможет при официальном обращении. "
                 "Можно пропустить 😊",
            attachments=[back_and_skip_keyboard()],
        )
        return

    if state == RegistrationState.AWAITING_LAST_NAME:
        await context.update_data(**{"draft.last_name": text})
        await context.set_state(RegistrationState.AWAITING_CUSTOMER_BIRTHDATE)
        await bot.send_message(
            user_id=user_id,
            text="Шаг 3 из 4 · Когда ваш день рождения? Обязательно поздравим! 🎂 (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard()],
        )
        return

    if state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        bd = _parse_date(text)
        if bd is None:
            await bot.send_message(
                user_id=user_id,
                text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                attachments=[back_and_skip_keyboard()],
            )
            return
        await context.update_data(**{"draft.birthdate": str(bd)})
        data = await context.get_data()
        children = data.get("draft.children", [])
        await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
        if not children:
            await bot.send_message(
                user_id=user_id,
                text="Шаг 4 из 4 · Как зовут вашего ребёнка?",
                attachments=[buy_for_self_keyboard()],
            )
        else:
            await bot.send_message(
                user_id=user_id,
                text="Как зовут следующего ребёнка?",
                attachments=[back_keyboard()],
            )
        return

    if state == RegistrationState.AWAITING_CHILD_NAME:
        data = await context.get_data()
        children = data.get("draft.children", [])
        children.append({"name": text, "gender": None, "birthdate": None})
        await context.update_data(**{"draft.children": children})
        n = len(children)
        await context.set_state(RegistrationState.AWAITING_CHILD_GENDER)
        await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 1 из 3 · Ваш ребёнок — мальчик или девочка? "
                 "Подберём подходящие предложения:",
            attachments=[gender_keyboard()],
        )
        return

    if state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        bd = _parse_date(text)
        if bd is None:
            await bot.send_message(
                user_id=user_id,
                text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                attachments=[back_and_skip_keyboard()],
            )
            return
        data = await context.get_data()
        children = data.get("draft.children", [])
        if children:
            children[-1]["birthdate"] = str(bd)
        await context.update_data(**{"draft.children": children})
        n = len(children)
        await context.set_state(RegistrationState.AWAITING_MORE_CHILDREN)
        await bot.send_message(
            user_id=user_id,
            text=f"Ребёнок {n} · шаг 3 из 3 · Хотите добавить ещё одного ребёнка?",
            attachments=[yes_no_keyboard("more_children:yes", "more_children:no")],
        )
        return

    # Survey confirmation card inline edit
    if state == RegistrationState.AWAITING_CONFIRMATION:
        data = await context.get_data()
        field = data.get("draft.editing_field")
        if field:
            if field == "birthdate":
                val = _parse_date(text)
                if val is None:
                    await bot.send_message(
                        user_id=user_id,
                        text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):"
                    )
                    return
                val = str(val)
            else:
                val = text
            await context.update_data(**{f"draft.{field}": val, "draft.editing_field": None})
            data = await context.get_data()
            children = data.get("draft.children", [])
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
                    text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):"
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
        await bot.send_message(
            user_id=user_id,
            text="Ваш ребёнок — мальчик или девочка?",
            attachments=[gender_keyboard()],
        )
        return

    if state == ProfileState.ADDING_CHILD_BIRTHDATE:
        bd = _parse_date(text)
        if bd is None:
            await bot.send_message(
                user_id=user_id,
                text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):"
            )
            return
        if customer is None:
            async with get_session_factory()() as session:
                customer = await customer_model.get_by_max_id(session, user_id)
        if customer is None:
            return
        data = await context.get_data()
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
                        await coupon_model.create_survey_coupon(session, customer.id)
                    children = await child_model.get_by_customer(session, customer.id)
        except Exception:
            logger.exception("Add child failed")
            await bot.send_message(user_id=user_id, text="Не удалось сохранить. Попробуйте ещё раз.")
            return
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text="👶 Ваши дети:",
            attachments=[children_list_keyboard(children)],
        )
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
                    text="Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):"
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
