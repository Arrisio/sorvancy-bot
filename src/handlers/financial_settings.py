"""Scenario 22: Owner views and edits financial parameters."""
import logging

from maxapi.types import MessageCreated
from maxapi.filters import F
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton

from src.keyboards import FINANCIAL_SETTINGS_BTN_TEXT
from src.db.connection import get_session_factory
from src.models import financial_config as financial_config_model
from src.db.orm import Staff

logger = logging.getLogger(__name__)


def financial_summary_text(cfg) -> str:
    return (
        "⚙️ Финансовые настройки\n\n"
        f"Скидка при регистрации: {cfg.registration_discount_pct}%\n\n"
        "🎁 Купон за анкету\n"
        f"Сумма: {cfg.survey_coupon_value} ₽ · "
        f"Срок: {cfg.survey_coupon_valid_days} дн · "
        f"Мин. сумма покупки: {cfg.survey_coupon_min_purchase} ₽\n\n"
        "🎂 Купон на день рождения\n"
        f"Сумма: {cfg.birthday_coupon_value} ₽ · "
        f"Срок: {cfg.birthday_coupon_valid_days} дн · "
        f"Мин. сумма покупки: {cfg.birthday_coupon_min_purchase} ₽"
    )


def financial_summary_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(
        text="✏️ Скидка при регистрации",
        payload="financial:edit:registration_discount_pct",
    ))
    builder.row(CallbackButton(text="✏️ Купон за анкету", payload="financial:card:survey"))
    builder.row(CallbackButton(text="✏️ Купон на день рождения", payload="financial:card:birthday"))
    return builder.as_markup()


def survey_coupon_card_text(cfg) -> str:
    return (
        "🎁 Купон за анкету\n"
        f"Сумма: {cfg.survey_coupon_value} ₽\n"
        f"Срок действия: {cfg.survey_coupon_valid_days} дней\n"
        f"Макс. % от покупки: {cfg.survey_coupon_max_pct}%"
    )


def birthday_coupon_card_text(cfg) -> str:
    return (
        "🎂 Купон на день рождения\n"
        f"Сумма: {cfg.birthday_coupon_value} ₽\n"
        f"Срок действия: {cfg.birthday_coupon_valid_days} дней\n"
        f"Макс. % от покупки: {cfg.birthday_coupon_max_pct}%"
    )


def coupon_card_keyboard(coupon_type: str):
    prefix = "survey" if coupon_type == "survey" else "birthday"
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✏️ Сумма", payload=f"financial:edit:{prefix}_coupon_value"),
        CallbackButton(text="✏️ Срок", payload=f"financial:edit:{prefix}_coupon_valid_days"),
        CallbackButton(text="✏️ % от покупки", payload=f"financial:edit:{prefix}_coupon_max_pct"),
    )
    builder.row(CallbackButton(text="← Назад", payload="financial:back"))
    return builder.as_markup()


async def register_financial_settings_handlers(dp):

    @dp.message_created(F.message.body.text == FINANCIAL_SETTINGS_BTN_TEXT)
    async def on_financial_settings_btn(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        route: str = "registration",
    ):
        if route != "staff" or staff is None or not staff.is_owner:
            return
        async with get_session_factory()() as session:
            cfg = await financial_config_model.get_or_create(session)
        sent = await event.bot.send_message(
            user_id=event.message.sender.user_id,
            text=financial_summary_text(cfg),
            attachments=[financial_summary_keyboard()],
        )
        await context.update_data(
            financial_card_mid=sent.message.body.mid,
            financial_card_type="summary",
        )
