import logging
from datetime import date

from maxapi.context import MemoryContext

from src.states import RegistrationState
from src.keyboards import (
    registered_keyboard,
    cancel_keyboard,
    back_keyboard,
    back_and_skip_keyboard,
    gender_keyboard,
    buy_for_self_keyboard,
    yes_no_keyboard,
    confirmation_card_keyboard,
    contact_keyboard,
    resume_survey_keyboard,
    profile_card_keyboard,
)
from src.handlers.registration import _format_confirmation
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model
from src.models import coupon as coupon_model
from src.models import financial_config as financial_config_model
from src.services.discount import coupon_issued_notification
from src.handlers.callbacks._common import (
    _append_step_mid,
    _delete_step_mids,
    _send_step,
    _persist_survey_draft,
)

logger = logging.getLogger(__name__)


async def handle_survey_callback(
    bot, user_id: int, state: str, payload: str, context: MemoryContext
) -> bool:
    """Handle survey-domain callbacks. Returns True if payload was consumed."""

    if payload == "survey:start":
        async with get_session_factory()() as session:
            cust = await customer_model.get_by_max_id(session, user_id)
        if not cust:
            return True
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
            from src.handlers.profile import _profile_text
            await bot.send_message(
                user_id=user_id,
                text=_profile_text(cust, children),
                attachments=[profile_card_keyboard(cust.opt_out_marketing)],
            )
            return True
        if cust.survey_draft:
            await bot.send_message(
                user_id=user_id,
                text=_format_resume_message(cust.survey_draft),
                attachments=[resume_survey_keyboard()],
            )
            return True
        await context.update_data(**{"draft.children": [], "draft.bought_for_self": False, "step_mids": []})
        await context.set_state(RegistrationState.AWAITING_FIRST_NAME)
        await _persist_survey_draft(context, user_id)
        await _send_step(bot, user_id, context,
            "Шаг 1 из 4 · Как к вам обращаться? Введите имя или имя и отчество:",
            cancel_keyboard("survey:cancel"))
        return True

    if payload == "survey:resume":
        async with get_session_factory()() as session:
            cust = await customer_model.get_by_max_id(session, user_id)
        if not cust or not cust.survey_draft:
            await context.update_data(**{"draft.children": [], "draft.bought_for_self": False})
            await context.set_state(RegistrationState.AWAITING_FIRST_NAME)
            await _persist_survey_draft(context, user_id)
            await _send_step(bot, user_id, context,
                "Шаг 1 из 4 · Как к вам обращаться? Введите имя или имя и отчество:",
                cancel_keyboard("survey:cancel"))
            return True
        draft = cust.survey_draft
        resume_state = draft.get("_state", RegistrationState.AWAITING_FIRST_NAME)
        restore_data = {k: v for k, v in draft.items() if k != "_state"}
        await context.update_data(**restore_data)
        await context.set_state(resume_state)
        await _resend_survey_step(bot, user_id, resume_state, context)
        return True

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
        await _send_step(bot, user_id, context,
            "Шаг 1 из 4 · Как к вам обращаться? Введите имя или имя и отчество:",
            cancel_keyboard("survey:cancel"))
        return True

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
        return True

    if payload == "survey:skip":
        data = await context.get_data()
        mid = data.get("survey_offer_mid")
        if mid:
            try:
                await bot.delete_message(message_id=mid)
            except Exception:
                pass
        return True

    if payload == "skip":
        if state in (
            RegistrationState.AWAITING_LAST_NAME,
            RegistrationState.AWAITING_CUSTOMER_BIRTHDATE,
            RegistrationState.AWAITING_CHILD_BIRTHDATE,
        ):
            await _handle_survey_skip(bot, user_id, state, context)
            return True
        return False

    if payload == "buy_for_self" and state == RegistrationState.AWAITING_CHILD_NAME:
        await context.update_data(**{"draft.bought_for_self": True})
        await context.set_state(RegistrationState.AWAITING_CONFIRMATION)
        await _persist_survey_draft(context, user_id)
        data = await context.get_data()
        await _send_confirmation_card(bot, user_id, data, context)
        return True

    if payload == "back":
        if state in RegistrationState.SURVEY_STATES:
            await _handle_survey_back(bot, user_id, state, context)
            return True
        return False

    if state == RegistrationState.AWAITING_CHILD_GENDER and payload.startswith("gender:"):
        gender = payload.split(":")[-1]
        data = await context.get_data()
        children = data.get("draft.children", [])
        if children:
            children[-1]["gender"] = gender
        await context.update_data(**{"draft.children": children})
        await context.set_state(RegistrationState.AWAITING_CHILD_BIRTHDATE)
        await _persist_survey_draft(context, user_id)
        await _resend_survey_step(bot, user_id, RegistrationState.AWAITING_CHILD_BIRTHDATE, context)
        return True

    if state == RegistrationState.AWAITING_MORE_CHILDREN and payload.startswith("more_children:"):
        if payload.endswith("yes"):
            await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
            await _persist_survey_draft(context, user_id)
            await _resend_survey_step(bot, user_id, RegistrationState.AWAITING_CHILD_NAME, context)
        else:
            await context.set_state(RegistrationState.AWAITING_CONFIRMATION)
            await _persist_survey_draft(context, user_id)
            data = await context.get_data()
            await _send_confirmation_card(bot, user_id, data, context)
        return True

    if state == RegistrationState.AWAITING_CONFIRMATION:
        if payload == "confirm:save":
            await context.set_state(RegistrationState.AWAITING_CONTACT)
            await _persist_survey_draft(context, user_id)
            await _send_step(bot, user_id, context,
                "Последний шаг — поделитесь контактом как запасным каналом связи. "
                "Если что-то случится с ботом, мы не потеряем вас! Это необязательно.",
                contact_keyboard())
            return True
        if payload.startswith("edit:"):
            field = payload[5:]
            await context.update_data(**{"draft.editing_field": field})
            labels = {
                "first_name": "Имя",
                "last_name": "Фамилия",
                "birthdate": "Дата рождения (ДД.ММ.ГГ или ДД.ММ.ГГГГ)",
            }
            label = labels.get(field, field)
            await bot.send_message(
                user_id=user_id,
                text=f"Введите новое значение — {label}:",
                attachments=[back_keyboard()],
            )
            return True
        return False

    if state == RegistrationState.AWAITING_CONTACT and payload == "contact:skip":
        await _complete_survey(bot, user_id, context)
        return True

    return False


async def _resend_survey_step(bot, user_id: int, state: str, context: MemoryContext) -> None:
    data = await context.get_data()
    children = data.get("draft.children", [])
    n = len(children)

    if state == RegistrationState.AWAITING_FIRST_NAME:
        await _send_step(bot, user_id, context,
            "Шаг 1 из 4 · Как к вам обращаться? Введите имя или имя и отчество:",
            cancel_keyboard("survey:cancel"))
    elif state == RegistrationState.AWAITING_LAST_NAME:
        await _send_step(bot, user_id, context,
            "Шаг 2 из 4 · Расскажите свою фамилию — поможет при официальном обращении. Можно пропустить 😊",
            back_and_skip_keyboard("survey:cancel"))
    elif state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        await _send_step(bot, user_id, context,
            "Шаг 3 из 4 · Когда ваш день рождения? Обязательно поздравим! 🎂\nПример: 12.05.90 или 12.05.1990",
            back_and_skip_keyboard("survey:cancel"))
    elif state == RegistrationState.AWAITING_CHILD_NAME:
        if not children:
            await _send_step(bot, user_id, context,
                "Шаг 4 из 4 · Как зовут вашего ребёнка?",
                buy_for_self_keyboard())
        else:
            await _send_step(bot, user_id, context,
                "Как зовут следующего ребёнка?",
                back_keyboard())
    elif state == RegistrationState.AWAITING_CHILD_GENDER:
        await _send_step(bot, user_id, context,
            f"Ребёнок {n} · шаг 1 из 3 · Ваш ребёнок — мальчик или девочка? Подберём подходящие предложения:",
            gender_keyboard())
    elif state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        await _send_step(bot, user_id, context,
            f"Ребёнок {n} · шаг 2 из 3 · Когда день рождения у ребёнка? Будем поздравлять! 🎉\nПример: 12.05.90 или 12.05.1990",
            back_and_skip_keyboard("survey:cancel"))
    elif state == RegistrationState.AWAITING_MORE_CHILDREN:
        await _send_step(bot, user_id, context,
            f"Ребёнок {n} · шаг 3 из 3 · Хотите добавить ещё одного ребёнка?",
            yes_no_keyboard("more_children:yes", "more_children:no"))
    elif state == RegistrationState.AWAITING_CONFIRMATION:
        await _send_confirmation_card(bot, user_id, data, context)
    elif state == RegistrationState.AWAITING_CONTACT:
        await _send_step(bot, user_id, context,
            "Последний шаг — поделитесь контактом как запасным каналом связи. "
            "Если что-то случится с ботом, мы не потеряем вас! Это необязательно.",
            contact_keyboard())


async def _handle_survey_skip(bot, user_id: int, state: str, context: MemoryContext) -> None:
    if state == RegistrationState.AWAITING_LAST_NAME:
        await context.update_data(**{"draft.last_name": None})
        target = RegistrationState.AWAITING_CUSTOMER_BIRTHDATE
    elif state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        await context.update_data(**{"draft.birthdate": None})
        target = RegistrationState.AWAITING_CHILD_NAME
    elif state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        data = await context.get_data()
        children = data.get("draft.children", [])
        if children:
            children[-1]["birthdate"] = None
        await context.update_data(**{"draft.children": children})
        target = RegistrationState.AWAITING_MORE_CHILDREN
    else:
        return
    await context.set_state(target)
    await _persist_survey_draft(context, user_id)
    await _resend_survey_step(bot, user_id, target, context)


async def _handle_survey_back(bot, user_id: int, state: str, context: MemoryContext) -> None:
    data = await context.get_data()

    if state == RegistrationState.AWAITING_LAST_NAME:
        target = RegistrationState.AWAITING_FIRST_NAME
    elif state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
        target = RegistrationState.AWAITING_LAST_NAME
    elif state == RegistrationState.AWAITING_CHILD_NAME:
        children = data.get("draft.children", [])
        target = RegistrationState.AWAITING_MORE_CHILDREN if children else RegistrationState.AWAITING_CUSTOMER_BIRTHDATE
    elif state == RegistrationState.AWAITING_CHILD_GENDER:
        children = list(data.get("draft.children", []))
        if children:
            children.pop()
        await context.update_data(**{"draft.children": children})
        target = RegistrationState.AWAITING_CHILD_NAME
    elif state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
        target = RegistrationState.AWAITING_CHILD_GENDER
    elif state == RegistrationState.AWAITING_MORE_CHILDREN:
        target = RegistrationState.AWAITING_CHILD_BIRTHDATE
    elif state == RegistrationState.AWAITING_CONFIRMATION:
        children = data.get("draft.children", [])
        target = RegistrationState.AWAITING_MORE_CHILDREN if children else RegistrationState.AWAITING_CUSTOMER_BIRTHDATE
    elif state == RegistrationState.AWAITING_CONTACT:
        target = RegistrationState.AWAITING_CONFIRMATION
    else:
        return

    await context.set_state(target)
    await _persist_survey_draft(context, user_id)
    await _resend_survey_step(bot, user_id, target, context)


async def _send_confirmation_card(bot, user_id: int, data: dict, context: MemoryContext) -> None:
    children = data.get("draft.children", [])
    sent = await bot.send_message(
        user_id=user_id,
        text=_format_confirmation(data),
        attachments=[confirmation_card_keyboard(has_children=bool(children))],
    )
    await _append_step_mid(context, sent.message.body.mid)
    await context.update_data(confirmation_card_mid=sent.message.body.mid)


async def _complete_survey(bot, user_id: int, context: MemoryContext) -> None:
    data = await context.get_data()
    children_draft = data.get("draft.children", [])

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
                    survey_completed=True,
                )
                for ch_data in children_draft:
                    bd = (
                        date.fromisoformat(ch_data["birthdate"])
                        if ch_data.get("birthdate")
                        else None
                    )
                    await child_model.create(
                        session,
                        customer_id=cust.id,
                        name=ch_data["name"],
                        gender=ch_data["gender"],
                        birthdate=bd,
                    )
                survey_coupon = None
                if not was_completed:
                    cfg = await financial_config_model.get_or_create(session)
                    survey_coupon = await coupon_model.create_survey_coupon(
                        session, cust.id,
                        value=cfg.survey_coupon_value,
                        max_pct=cfg.survey_coupon_max_pct,
                        valid_days=cfg.survey_coupon_valid_days,
                    )
                await customer_model.clear_survey_draft(session, user_id)
        logger.info("Survey saved for max_user_id=%s", user_id)
    except Exception:
        logger.exception("Survey save failed for max_user_id=%s", user_id)
        await bot.send_message(user_id=user_id, text="Ошибка при сохранении. Попробуйте ещё раз.")
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
            await bot.send_message(user_id=user_id, text=coupon_issued_notification(survey_coupon))
        except Exception:
            logger.warning("Could not send coupon notification to user %s", user_id)


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
