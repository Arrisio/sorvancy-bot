"""
Staff reply-keyboard handlers (scenarios 04, 09, 10).
Text and callback handling is in text_router.py and callback_router.py.
"""
import logging
from maxapi.types import MessageCreated
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import StaffState, RegistrationState
from src.keyboards import (
    confirm_add_seller_keyboard,
    delete_seller_keyboard,
    STAFF_FIND_BTN_TEXT,
    STAFF_LIST_BTN_TEXT,
)
from src.db.connection import get_session_factory
from src.models import staff as staff_model
from src.models import customer as customer_model
from src.models import coupon as coupon_model
from src.services.discount import staff_customer_profile_message
from src.keyboards import staff_profile_keyboard
from src.db.orm import Staff

logger = logging.getLogger(__name__)


async def register_staff_handlers(dp):

    # Scenario 04: contact card from superuser → register new seller
    @dp.message_created(F.message.body.attachments)
    async def on_contact_card(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        route: str = "registration",
    ):
        if route != "staff" or staff is None or not staff.is_owner:
            return
        attachments = event.message.body.attachments or []
        contact = None
        for att in attachments:
            if hasattr(att, "user_id") or (
                hasattr(att, "type") and getattr(att, "type", "") == "contact"
            ):
                contact = att
                break
        if contact is None:
            return

        max_user_id = getattr(contact, "user_id", None) or getattr(contact, "max_user_id", None)
        if not max_user_id:
            await event.message.answer("Не удалось извлечь данные из карточки контакта.")
            return

        phone = getattr(contact, "phone", None)
        first_name = getattr(contact, "first_name", None) or getattr(contact, "name", None)
        last_name = getattr(contact, "last_name", None)
        username = getattr(contact, "username", None)

        async with get_session_factory()() as session:
            existing = await staff_model.get_by_max_id(session, max_user_id)
        if existing:
            await event.message.answer(
                f"Продавец {first_name or max_user_id} уже зарегистрирован."
            )
            return

        await context.update_data(
            pending_seller_max_id=max_user_id,
            pending_seller_phone=phone,
            pending_seller_first_name=first_name,
            pending_seller_last_name=last_name,
            pending_seller_username=username,
        )
        name = " ".join(filter(None, [first_name, last_name])) or str(max_user_id)
        await event.message.answer(
            f"Добавить {name} как нового продавца?",
            attachments=[confirm_add_seller_keyboard(max_user_id)],
        )

    # Scenario 09: list all sellers
    @dp.message_created(F.message.body.text == STAFF_LIST_BTN_TEXT)
    async def on_staff_list(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        route: str = "registration",
    ):
        if route != "staff" or staff is None or not staff.is_owner:
            return
        async with get_session_factory()() as session:
            sellers = await staff_model.get_all_sellers(session)
        if not sellers:
            await event.message.answer("Продавцов не зарегистрировано.")
            return
        for seller in sellers:
            name = " ".join(filter(None, [seller.first_name, seller.last_name])) or "—"
            phone = seller.phone or "—"
            await event.message.answer(
                f"👤 {name}\nТелефон: {phone}",
                attachments=[delete_seller_keyboard(seller.id)],
            )

    # Scenario 10: trigger awaiting customer ID state
    @dp.message_created(F.message.body.text == STAFF_FIND_BTN_TEXT)
    async def on_find_profile_btn(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        route: str = "registration",
    ):
        if route != "staff":
            return
        await context.set_state(StaffState.AWAITING_CUSTOMER_ID)
        await event.message.answer("Пришлите номер клиента")


async def _send_customer_profile_by_id(bot, staff_user_id: int, customer_id: int):
    async with get_session_factory()() as session:
        customer = await customer_model.get_by_id(session, customer_id)
        if customer is None:
            await bot.send_message(
                user_id=staff_user_id,
                text=f"Клиент с номером {customer_id} не найден.",
            )
            return
        coupons = await coupon_model.get_active_by_customer(session, customer.id)

    text = staff_customer_profile_message(customer, coupons)
    await bot.send_message(
        user_id=staff_user_id,
        text=text,
        attachments=[staff_profile_keyboard(customer.id, coupons)],
    )
