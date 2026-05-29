"""
Single unified handler for all F.message.body.text events.
Routes to sub-handlers based on `route` (from middleware) and FSM state.
This avoids multiple handlers competing for the same event type.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_PERM_TZ = ZoneInfo("Asia/Yekaterinburg")

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
from src.models import financial_config as financial_config_model
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
    child_card_keyboard,
    coupon_display_name_keyboard,
    coupon_value_keyboard,
    coupon_days_keyboard,
    coupon_min_purchase_keyboard,
    broadcast_comment_keyboard,
)
import config
from src.handlers.registration import _format_confirmation, _parse_int_list
from src.handlers.profile import _profile_text, _child_text
from src.handlers.broadcast import _create_broadcast, _in_window, _ask_broadcast_recipients, _save_broadcast_source, _ask_broadcast_comment
from src.utils.dates import parse_birthday, parse_broadcast_dt
from src.handlers.staff import _send_customer_profile_by_id
from src.handlers.callbacks._common import _persist_survey_draft, _append_step_mid, _delete_step_mids, _send_step
from src.handlers.financial_settings import (
    financial_summary_text, financial_summary_keyboard,
    survey_coupon_card_text, birthday_coupon_card_text, coupon_card_keyboard,
)
from src.services.discount import coupon_issued_notification, survey_invite_text

logger = logging.getLogger(__name__)


async def _do_coupon_value_accepted(bot, user_id: int, context, val: int) -> None:
    data = await context.get_data()
    coupon_ctx = data.get("coupon_context", "seller")
    await context.update_data(coupon_draft_value=val)
    await context.set_state(StaffState.AWAITING_COUPON_DAYS)
    sent = await bot.send_message(
        user_id=user_id,
        text="Срок действия купона (в днях, минимум 7):",
        attachments=[coupon_days_keyboard()],
    )
    if coupon_ctx == "broadcast":
        await _append_step_mid(context, sent.message.body.mid)


async def _do_coupon_days_accepted(bot, user_id: int, context, days: int) -> None:
    data = await context.get_data()
    coupon_ctx = data.get("coupon_context", "seller")
    await context.update_data(coupon_draft_days=days)
    await context.set_state(StaffState.AWAITING_COUPON_MIN_PURCHASE)
    sent = await bot.send_message(
        user_id=user_id,
        text="Выберите минимальную сумму покупки для применения купона (в руб.) или введите своё значение:",
        attachments=[coupon_min_purchase_keyboard()],
    )
    if coupon_ctx == "broadcast":
        await _append_step_mid(context, sent.message.body.mid)


async def _do_coupon_min_purchase_accepted(bot, user_id: int, context, min_purchase: int) -> None:
    data = await context.get_data()
    coupon_ctx = data.get("coupon_context", "seller")
    value = data.get("coupon_draft_value")
    days = data.get("coupon_draft_days")
    await context.update_data(coupon_draft_min_purchase=min_purchase)
    expiry = datetime.now(timezone.utc) + timedelta(days=days)
    suggested = f"{value} ₽ до {expiry.strftime('%d.%m.%y')}"
    await context.update_data(coupon_draft_suggested_display_name=suggested)
    await context.set_state(StaffState.AWAITING_COUPON_DISPLAY_NAME)
    sent = await bot.send_message(
        user_id=user_id,
        text=(
            f"Название купона в кнопке (видит покупатель, макс. 40 символов).\n"
            f"Предложение: «{suggested}».\n"
            "Введите своё или нажмите «Принять»."
        ),
        attachments=[coupon_display_name_keyboard()],
    )
    if coupon_ctx == "broadcast":
        await _append_step_mid(context, sent.message.body.mid)


async def _apply_coupon_display_name(bot, user_id: int, context, display_name: str) -> None:
    data = await context.get_data()
    coupon_ctx = data.get("coupon_context", "seller")
    min_purchase = data.get("coupon_draft_min_purchase", 0)

    if coupon_ctx == "broadcast":
        await context.update_data(
            broadcast_coupon_value=data.get("coupon_draft_value"),
            broadcast_coupon_days=data.get("coupon_draft_days"),
            broadcast_coupon_min_purchase=min_purchase,
            broadcast_coupon_display_name=display_name,
            coupon_context=None,
        )
        await _ask_broadcast_recipients(bot, user_id, context)
        return

    customer_id = data.get("coupon_target_customer_id")
    value = data.get("coupon_draft_value")
    days = data.get("coupon_draft_days")
    issued_coupon = None
    cust = None
    try:
        async with get_session_factory()() as session:
            async with session.begin():
                issued_coupon = await coupon_model.create_seller_coupon(
                    session, customer_id, value, days, min_purchase, display_name
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
                text=coupon_issued_notification(issued_coupon),
            )
        except Exception:
            logger.warning("Could not notify customer %s of coupon issuance", cust.max_user_id)
    await _send_customer_profile_by_id(bot, user_id, customer_id)


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


def _validate_financial_field(field: str, val: int) -> str | None:
    if field == "registration_discount_pct":
        if val < 1 or val > 100:
            return "Введите число от 1 до 100."
    elif field.endswith("_value"):
        if val <= 0:
            return "Сумма должна быть больше 0."
    elif field.endswith("_valid_days"):
        if val <= 0:
            return "Срок должен быть больше 0."
    elif field.endswith("_min_purchase"):
        if val < 0:
            return "Введите целое число от 0 и выше."
    return None


async def _handle_staff_text(event, context, staff, state, text, user_id):
    bot = event.bot

    # Broadcast states (owner only)
    if staff.is_owner:
        if state == StaffState.AWAITING_BROADCAST_MSG:
            await _save_broadcast_source(event, context)
            return

        if state == StaffState.AWAITING_BROADCAST_RECIPIENTS:
            ids = list(dict.fromkeys(_parse_int_list(text)))
            if not ids:
                await _send_step(
                    bot, user_id, context,
                    "Не удалось разобрать список ID. Попробуйте ещё раз.\n"
                    "Шаг 3 из 4 · Пришлите номера клиентов (через запятую или с новой строки):",
                    cancel_keyboard("broadcast:cancel_create"),
                )
                return
            async with get_session_factory()() as session:
                eligible = await broadcast_model.get_eligible_customer_ids(session, ids)
            await context.update_data(broadcast_recipient_ids=eligible)
            await context.set_state(StaffState.AWAITING_BROADCAST_TIME)
            await _send_step(
                bot, user_id, context,
                f"Шаг 4 из 4 · Создана рассылка на {len(eligible)} получателей. Когда её начать?\n"
                f"Окно рассылки: {config.BROADCAST_WINDOW_START_HOUR}:00–{config.BROADCAST_WINDOW_END_HOUR}:00.\n"
                "Укажите дату или воспользуйтесь кнопками:\n"
                f"  • «25.06» — 25 июня в {config.BROADCAST_WINDOW_START_HOUR}:00\n"
                "  • «25.06 14:30» — 25 июня в 14:30",
                broadcast_start_keyboard(),
            )
            return

        if state == StaffState.AWAITING_BROADCAST_TIME:
            scheduled_at, err = parse_broadcast_dt(text, _PERM_TZ, config.BROADCAST_WINDOW_START_HOUR)
            if err:
                await _send_step(
                    bot, user_id, context,
                    f"Шаг 4 из 5 · {err}:\n"
                    f"  • «25.06» — 25 июня в {config.BROADCAST_WINDOW_START_HOUR}:00\n"
                    "  • «25.06 14:30» — 25 июня в 14:30",
                    broadcast_start_keyboard(),
                )
                return
            if not _in_window(scheduled_at):
                await _send_step(
                    bot, user_id, context,
                    f"Шаг 4 из 5 · Время {scheduled_at.strftime('%H:%M')} недоступно. "
                    f"Укажите с {config.BROADCAST_WINDOW_START_HOUR}:00 "
                    f"до {config.BROADCAST_WINDOW_END_HOUR}:00:",
                    broadcast_start_keyboard(),
                )
                return
            await _ask_broadcast_comment(bot, user_id, context, scheduled_at)
            return

        if state == StaffState.AWAITING_BROADCAST_COMMENT:
            await context.update_data(broadcast_comment=text)
            data = await context.get_data()
            scheduled_at = data.get("broadcast_scheduled_at")
            await context.set_state(RegistrationState.REGISTERED)
            await _create_broadcast(bot, user_id, context, scheduled_at)
            return

    # Scenario 22: financial parameter input
    if state == StaffState.AWAITING_FINANCIAL_PARAM_VALUE:
        data = await context.get_data()
        field = data.get("financial_editing_field")
        prompt_mid = data.get("financial_prompt_mid")
        card_mid = data.get("financial_card_mid")
        card_type = data.get("financial_card_type", "summary")

        if field is None:
            await context.set_state(RegistrationState.REGISTERED)
            return

        try:
            val = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id, text="Введите целое число.",
                attachments=[cancel_keyboard("financial:cancel")],
            )
            return

        error = _validate_financial_field(field, val)
        if error:
            await bot.send_message(
                user_id=user_id, text=error,
                attachments=[cancel_keyboard("financial:cancel")],
            )
            return

        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    cfg = await financial_config_model.update_field(session, **{field: val})
        except Exception:
            logger.exception("FinancialConfig update failed for field=%s", field)
            await bot.send_message(
                user_id=user_id, text="Не удалось сохранить. Попробуйте ещё раз.",
                attachments=[cancel_keyboard("financial:cancel")],
            )
            return

        if prompt_mid:
            try:
                await bot.delete_message(message_id=prompt_mid)
            except Exception:
                pass

        await context.set_state(RegistrationState.REGISTERED)
        await context.update_data(financial_editing_field=None, financial_prompt_mid=None)

        if card_type == "survey":
            card_text = survey_coupon_card_text(cfg)
            keyboard = coupon_card_keyboard("survey")
        elif card_type == "birthday":
            card_text = birthday_coupon_card_text(cfg)
            keyboard = coupon_card_keyboard("birthday")
        else:
            card_text = financial_summary_text(cfg)
            keyboard = financial_summary_keyboard()

        if card_mid:
            try:
                await bot.edit_message(message_id=card_mid, text=card_text, attachments=[keyboard])
            except Exception:
                await bot.send_message(user_id=user_id, text=card_text, attachments=[keyboard])
        else:
            await bot.send_message(user_id=user_id, text=card_text, attachments=[keyboard])
        return

    # Scenario 15 Flow B / sub-scenario 21: coupon issuance
    if state == StaffState.AWAITING_COUPON_VALUE:
        try:
            val = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id,
                text="Введите целое число.",
                attachments=[coupon_value_keyboard()],
            )
            return
        if val < 100 or val > 5000:
            await bot.send_message(
                user_id=user_id,
                text="Введите сумму от 100 до 5000 рублей.",
                attachments=[coupon_value_keyboard()],
            )
            return
        await _do_coupon_value_accepted(bot, user_id, context, val)
        return

    if state == StaffState.AWAITING_COUPON_DAYS:
        try:
            days = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id,
                text="Введите целое число.",
                attachments=[coupon_days_keyboard()],
            )
            return
        if days < 7:
            await bot.send_message(
                user_id=user_id,
                text="Срок должен быть не менее 7 дней.",
                attachments=[coupon_days_keyboard()],
            )
            return
        await _do_coupon_days_accepted(bot, user_id, context, days)
        return

    if state == StaffState.AWAITING_COUPON_MIN_PURCHASE:
        try:
            min_purchase = int(text)
        except ValueError:
            await bot.send_message(
                user_id=user_id,
                text="Введите целое число.",
                attachments=[coupon_min_purchase_keyboard()],
            )
            return
        if min_purchase < 0:
            await bot.send_message(
                user_id=user_id,
                text="Введите целое число от 0 и выше.",
                attachments=[coupon_min_purchase_keyboard()],
            )
            return
        await _do_coupon_min_purchase_accepted(bot, user_id, context, min_purchase)
        return

    if state == StaffState.AWAITING_COUPON_DISPLAY_NAME:
        if len(text) > 40:
            data = await context.get_data()
            coupon_ctx = data.get("coupon_context", "seller")
            sent = await bot.send_message(
                user_id=user_id,
                text="Название не должно превышать 40 символов. Введите короче или нажмите «Принять».",
                attachments=[coupon_display_name_keyboard()],
            )
            if coupon_ctx == "broadcast":
                await _append_step_mid(context, sent.message.body.mid)
            return
        await _apply_coupon_display_name(bot, user_id, context, text)
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
            text="Вас приветствует бот магазина «Сорванцы»!",
            attachments=[kb],
        )


async def _handle_customer_text(event, context, customer, state, text, user_id, route="customer"):
    bot = event.bot

    # Survey states
    if state == RegistrationState.AWAITING_FIRST_NAME:
        await context.update_data(**{"draft.first_name": text})
        await context.set_state(RegistrationState.AWAITING_LAST_NAME)
        await _persist_survey_draft(context, user_id)
        await _send_step(
            bot, user_id, context,
            "Шаг 2 из 4 · Расскажите свою фамилию — поможет при официальном обращении. "
            "Можно пропустить 😊",
            back_and_skip_keyboard("survey:cancel"),
        )
        return

    if state == RegistrationState.AWAITING_LAST_NAME:
        await context.update_data(**{"draft.last_name": text})
        await context.set_state(RegistrationState.AWAITING_CUSTOMER_BIRTHDATE)
        await _persist_survey_draft(context, user_id)
        await _send_step(
            bot, user_id, context,
            f"Шаг 3 из 4 · Когда ваш день рождения? Обязательно поздравим! 🎂\nПример: 12.05.90 или 12.05.1990",
            back_and_skip_keyboard("survey:cancel"),
        )
        return

    if state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        bd, err = parse_birthday(text)
        if err:
            await _send_step(
                bot, user_id, context,
                err,
                back_and_skip_keyboard("survey:cancel"),
            )
            return
        await context.update_data(**{"draft.birthdate": str(bd)})
        data = await context.get_data()
        children = data.get("draft.children", [])
        await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
        await _persist_survey_draft(context, user_id)
        if not children:
            await _send_step(
                bot, user_id, context,
                "Шаг 4 из 4 · Как зовут вашего ребёнка?",
                buy_for_self_keyboard(),
            )
        else:
            await _send_step(
                bot, user_id, context,
                f"Ребёнок {len(children) + 1} · шаг 1 из 3 · Как зовут ребёнка?",
                back_keyboard(),
            )
        return

    if state == RegistrationState.AWAITING_CHILD_NAME:
        data = await context.get_data()
        children = data.get("draft.children", [])
        children.append({"name": text, "gender": None, "birthdate": None})
        await context.update_data(**{"draft.children": children})
        n = len(children)
        await context.set_state(RegistrationState.AWAITING_CHILD_GENDER)
        await _persist_survey_draft(context, user_id)
        await _send_step(
            bot, user_id, context,
            f"Ребёнок {n} · шаг 1 из 3 · Ваш ребёнок — мальчик или девочка? "
            "Подберём подходящие предложения:",
            gender_keyboard(),
        )
        return

    if state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        bd, err = parse_birthday(text)
        if err:
            await _send_step(
                bot, user_id, context,
                err,
                back_and_skip_keyboard("survey:cancel"),
            )
            return
        data = await context.get_data()
        children = data.get("draft.children", [])
        if children:
            children[-1]["birthdate"] = str(bd)
        await context.update_data(**{"draft.children": children})
        n = len(children)
        await context.set_state(RegistrationState.AWAITING_MORE_CHILDREN)
        await _persist_survey_draft(context, user_id)
        await _send_step(
            bot, user_id, context,
            f"Ребёнок {n} · шаг 3 из 3 · Хотите добавить ещё одного ребёнка?",
            yes_no_keyboard("more_children:yes", "more_children:no"),
        )
        return

    # Survey confirmation card inline edit
    if state == RegistrationState.AWAITING_CONFIRMATION:
        data = await context.get_data()
        field = data.get("draft.editing_field")
        if field:
            if field == "birthdate":
                val, err = parse_birthday(text)
                if err:
                    await _send_step(
                        bot, user_id, context,
                        err,
                        back_keyboard(),
                    )
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
            val, err = parse_birthday(text)
            if err:
                await bot.send_message(
                    user_id=user_id,
                    text=err,
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
        await _send_step(
            bot, user_id, context,
            "Ваш ребёнок — мальчик или девочка?",
            gender_keyboard(),
        )
        return

    if state == ProfileState.ADDING_CHILD_BIRTHDATE:
        bd, err = parse_birthday(text)
        if err:
            await bot.send_message(
                user_id=user_id,
                text=err,
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
                        cfg = await financial_config_model.get_or_create(session)
                        new_survey_coupon = await coupon_model.create_survey_coupon(
                            session, customer.id,
                            value=cfg.survey_coupon_value,
                            min_purchase=cfg.survey_coupon_min_purchase,
                            valid_days=cfg.survey_coupon_valid_days,
                        )
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

    if state == ProfileState.EDITING_CHILD_FIELD:
        if customer is None:
            async with get_session_factory()() as session:
                customer = await customer_model.get_by_max_id(session, user_id)
        if customer is None:
            return
        data = await context.get_data()
        child_id = data.get("edit.child_id")
        child_field = data.get("edit.child_field")
        if child_field == "birthdate":
            val, err = parse_birthday(text)
            if err:
                await bot.send_message(
                    user_id=user_id,
                    text=err,
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
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text=_child_text(updated),
            attachments=[child_card_keyboard(child_id)],
        )
        return

    # Fallback: unrecognised message in idle state
    if state in (RegistrationState.REGISTERED, None):
        if route == "registration":
            await bot.send_message(
                user_id=user_id,
                text="Вас приветствует бот магазина «Сорванцы»!",
                attachments=[unregistered_keyboard()],
            )
        else:
            text = "Вас приветствует бот магазина «Сорванцы»!"
            if customer is not None and not customer.survey_completed:
                async with get_session_factory()() as session:
                    cfg = await financial_config_model.get_or_create(session)
                text += f"\n{survey_invite_text(cfg.survey_coupon_value)}"
            await bot.send_message(
                user_id=user_id,
                text=text,
                attachments=[registered_keyboard(
                    survey_completed=customer.survey_completed if customer else True,
                    survey_draft=customer.survey_draft if customer else None,
                )],
            )
