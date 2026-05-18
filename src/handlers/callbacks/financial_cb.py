"""Callbacks for scenario 22: financial settings."""
import logging

from maxapi.context import MemoryContext

from src.states import StaffState, RegistrationState
from src.db.connection import get_session_factory
from src.models import financial_config as financial_config_model
from src.keyboards import cancel_keyboard
from src.handlers.financial_settings import (
    financial_summary_text,
    financial_summary_keyboard,
    survey_coupon_card_text,
    birthday_coupon_card_text,
    coupon_card_keyboard,
)

logger = logging.getLogger(__name__)

_FIELD_PROMPTS = {
    "registration_discount_pct": "Введите новое значение скидки при регистрации (1–100):",
    "survey_coupon_value": "Введите сумму купона за анкету (целое число ₽, > 0):",
    "survey_coupon_valid_days": "Введите срок действия купона за анкету (целое число дней, > 0):",
    "survey_coupon_max_pct": "Введите макс. % от покупки для купона за анкету (1–100):",
    "birthday_coupon_value": "Введите сумму купона на день рождения (целое число ₽, > 0):",
    "birthday_coupon_valid_days": "Введите срок действия купона на день рождения (целое число дней, > 0):",
    "birthday_coupon_max_pct": "Введите макс. % от покупки для купона на день рождения (1–100):",
}


async def _edit_or_send_card(bot, user_id: int, context: MemoryContext, card_mid, text: str, keyboard):
    if card_mid:
        try:
            await bot.edit_message(message_id=card_mid, text=text, attachments=[keyboard])
            return
        except Exception:
            pass
    sent = await bot.send_message(user_id=user_id, text=text, attachments=[keyboard])
    await context.update_data(financial_card_mid=sent.message.body.mid)


async def handle_financial_callback(
    bot, user_id: int, state: str, payload: str, context: MemoryContext
) -> None:
    data = await context.get_data()
    card_mid = data.get("financial_card_mid")
    card_type = data.get("financial_card_type", "summary")

    if payload.startswith("financial:card:"):
        coupon_type = payload.split(":")[-1]
        async with get_session_factory()() as session:
            cfg = await financial_config_model.get_or_create(session)
        if coupon_type == "survey":
            text = survey_coupon_card_text(cfg)
            keyboard = coupon_card_keyboard("survey")
        else:
            text = birthday_coupon_card_text(cfg)
            keyboard = coupon_card_keyboard("birthday")
        await context.update_data(financial_card_type=coupon_type)
        await _edit_or_send_card(bot, user_id, context, card_mid, text, keyboard)
        return

    if payload == "financial:back":
        async with get_session_factory()() as session:
            cfg = await financial_config_model.get_or_create(session)
        await context.update_data(financial_card_type="summary")
        await _edit_or_send_card(
            bot, user_id, context, card_mid,
            financial_summary_text(cfg), financial_summary_keyboard(),
        )
        return

    if payload.startswith("financial:edit:"):
        field = payload[len("financial:edit:"):]
        prompt = _FIELD_PROMPTS.get(field)
        if prompt is None:
            return
        await context.update_data(financial_editing_field=field)
        await context.set_state(StaffState.AWAITING_FINANCIAL_PARAM_VALUE)
        sent = await bot.send_message(
            user_id=user_id, text=prompt, attachments=[cancel_keyboard("financial:cancel")]
        )
        await context.update_data(financial_prompt_mid=sent.message.body.mid)
        return

    if payload == "financial:cancel":
        prompt_mid = data.get("financial_prompt_mid")
        if prompt_mid:
            try:
                await bot.delete_message(message_id=prompt_mid)
            except Exception:
                pass
        await context.set_state(RegistrationState.REGISTERED)
        await context.update_data(financial_editing_field=None, financial_prompt_mid=None)
        async with get_session_factory()() as session:
            cfg = await financial_config_model.get_or_create(session)
        if card_type == "survey":
            text = survey_coupon_card_text(cfg)
            keyboard = coupon_card_keyboard("survey")
        elif card_type == "birthday":
            text = birthday_coupon_card_text(cfg)
            keyboard = coupon_card_keyboard("birthday")
        else:
            text = financial_summary_text(cfg)
            keyboard = financial_summary_keyboard()
        await _edit_or_send_card(bot, user_id, context, card_mid, text, keyboard)
        return
