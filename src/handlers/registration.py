import re
import logging

from maxapi.types import MessageCreated
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import RegistrationState
from src.keyboards import (
    registered_keyboard,
    unregistered_keyboard,
    survey_offer_keyboard,
    REGISTER_BTN_TEXT,
)
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import financial_config as financial_config_model
from src.services.discount import registration_complete_message, survey_offer_message
import config

logger = logging.getLogger(__name__)


def _parse_int_list(text: str) -> list[int]:
    return [int(p) for p in re.split(r"\D+", text.strip()) if p]


def _format_confirmation(data: dict) -> str:
    fn = data.get("draft.first_name") or "—"
    ln = data.get("draft.last_name") or ""
    bd = data.get("draft.birthdate") or "не указана"
    name_line = f"👤 {fn} {ln}".strip()
    lines = [
        "📋 Проверьте данные перед сохранением:",
        "",
        name_line,
        f"🎂 {bd}",
    ]
    children = data.get("draft.children", [])
    if children:
        lines.append("")
        lines.append("👧 Дети:")
        for i, ch in enumerate(children, 1):
            g = "Мальчик" if ch.get("gender") == "male" else "Девочка"
            b = ch.get("birthdate") or "—"
            lines.append(f"  {i}. {ch['name']} · {g} · {b}")
    return "\n".join(lines)


async def register_registration_handlers(dp):

    @dp.message_created(F.message.body.text == REGISTER_BTN_TEXT)
    async def on_register_button(event: MessageCreated, context: MemoryContext):
        user_id = event.message.sender.user_id
        username = getattr(event.message.sender, "name", None)

        async with get_session_factory()() as session:
            existing = await customer_model.get_by_max_id(session, user_id)
        if existing:
            await event.message.answer(
                "Вы уже зарегистрированы!",
                attachments=[registered_keyboard()],
            )
            return

        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    cfg = await financial_config_model.get_or_create(session)
                    registration_pct = cfg.registration_discount_pct
                    await customer_model.create(
                        session,
                        max_user_id=user_id,
                        max_username=username,
                        discount_percent=registration_pct,
                    )
            logger.info("Registered max_user_id=%s (phase 1)", user_id)
        except Exception:
            logger.exception("Registration failed for max_user_id=%s", user_id)
            await event.message.answer(
                "Ошибка при регистрации. Попробуйте позже.",
                attachments=[unregistered_keyboard()],
            )
            return

        await context.clear()
        await context.update_data(
            max_user_id=user_id,
            max_username=username,
            **{"draft.children": [], "draft.bought_for_self": False},
        )
        await context.set_state(RegistrationState.REGISTERED)

        await event.bot.send_message(
            user_id=user_id,
            text=registration_complete_message(registration_pct),
            attachments=[registered_keyboard()],
        )

        try:
            sended = await event.bot.send_message(
                user_id=user_id,
                text=survey_offer_message(),
                attachments=[survey_offer_keyboard()],
            )
            await context.update_data(survey_offer_mid=sended.message.body.mid)
        except Exception:
            logger.debug("Could not store survey offer message id")
