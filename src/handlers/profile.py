"""
Profile display handler (scenario 05).
Text and callback handling is in text_router.py and callback_router.py.
"""
import logging
from maxapi.types import MessageCreated
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import RegistrationState
from src.keyboards import (
    registered_keyboard,
    profile_card_keyboard,
    empty_profile_keyboard,
    MY_PROFILE_BTN_TEXT,
)
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model
from src.db.orm import Customer

logger = logging.getLogger(__name__)


def _profile_text(customer, children: list) -> str:
    lines = [
        "👤 Ваш профиль",
        "",
        f"Имя: {customer.first_name or 'не указано'}",
        f"Фамилия: {customer.last_name or 'не указано'}",
        f"Дата рождения: {customer.birthdate.strftime('%d.%m.%Y') if customer.birthdate else 'не указано'}",
        f"Телефон: {customer.phone or 'не указано'}",
    ]
    if children:
        lines.append("")
        lines.append("👧 Дети:")
        for i, ch in enumerate(children, 1):
            g = "Мальчик" if ch.gender == "male" else "Девочка"
            b = ch.birthdate.strftime("%d.%m.%Y") if ch.birthdate else "—"
            lines.append(f"  {i}. {ch.name} · {g} · {b}")
    return "\n".join(lines)


def _child_text(child) -> str:
    g = "Мальчик" if child.gender == "male" else "Девочка"
    b = child.birthdate.strftime("%d.%m.%Y") if child.birthdate else "—"
    return f"👧 {child.name}\nПол: {g}\nДата рождения: {b}"


async def register_profile_handlers(dp):

    @dp.message_created(F.message.body.text == MY_PROFILE_BTN_TEXT)
    async def on_profile_btn(
        event: MessageCreated,
        context: MemoryContext,
        customer: Customer | None = None,
        route: str = "registration",
    ):
        if route not in ("customer", "staff"):
            return
        user_id = event.message.sender.user_id
        if customer is None:
            async with get_session_factory()() as session:
                customer = await customer_model.get_by_max_id(session, user_id)
        if customer is None:
            await event.message.answer(
                "Вы не зарегистрированы.", attachments=[registered_keyboard()]
            )
            return
        if not customer.survey_completed:
            text = (
                "👤 Ваш профиль\n\nАнкета не завершена — есть незаполненные данные."
                if customer.survey_draft
                else "👤 Ваш профиль\n\nАнкета не заполнена"
            )
            await event.message.answer(
                text,
                attachments=[empty_profile_keyboard()],
            )
            return
        async with get_session_factory()() as session:
            children = await child_model.get_by_customer(session, customer.id)
        await event.message.answer(
            _profile_text(customer, children),
            attachments=[profile_card_keyboard(customer.opt_out_marketing)],
        )
