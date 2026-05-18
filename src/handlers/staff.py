"""
Staff reply-keyboard handlers (scenarios 04, 09, 10).
Text and callback handling is in text_router.py and callback_router.py.
"""
import re
import logging
from maxapi.types import MessageCreated
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import StaffState, RegistrationState
from src.keyboards import (
    delete_seller_keyboard,
    cancel_keyboard,
    STAFF_FIND_BTN_TEXT,
    STAFF_LIST_BTN_TEXT,
    ADD_SELLER_BTN_TEXT,
)
from src.db.connection import get_session_factory
from src.models import staff as staff_model
from src.models import customer as customer_model
from src.models import coupon as coupon_model
from src.services.discount import staff_customer_profile_message
from src.services.invite import make_invite_token, staff_invite_deeplink
from src.keyboards import staff_profile_keyboard
from src.db.orm import Staff, Customer
from src.handlers.callbacks.survey import _complete_survey


def _phone_from_vcf(vcf_info: str | None) -> str | None:
    if not vcf_info:
        return None
    m = re.search(r'TEL[^:\r\n]*:(\+?\d+)', vcf_info)
    return m.group(1) if m else None

logger = logging.getLogger(__name__)


async def register_staff_handlers(dp):

    # Survey contact path: customer shares phone during registration (scenario 02)
    @dp.message_created(F.message.body.attachments)
    async def on_contact_card(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        customer: Customer | None = None,
        route: str = "registration",
    ):
        # Broadcast content: staff owner sends any attachment as broadcast message source
        if route == "staff" and staff is not None and staff.is_owner:
            state = await context.get_state()
            if state == StaffState.AWAITING_BROADCAST_MSG:
                from src.handlers.broadcast import _save_broadcast_source
                await _save_broadcast_source(event, context)
                return

        if route != "customer":
            return
        state = await context.get_state()
        if state != RegistrationState.AWAITING_CONTACT:
            return
        user_id = event.message.sender.user_id
        attachments = event.message.body.attachments or []
        contact = None
        for att in attachments:
            if hasattr(att, "type") and getattr(att, "type", "") == "contact":
                contact = att
                break
        if contact is not None:
            vcf_info = getattr(getattr(contact, "payload", None), "vcf_info", None)
            phone = _phone_from_vcf(vcf_info)
            if phone:
                await context.update_data(**{"draft.phone": phone})
            await _complete_survey(event.bot, user_id, context)
        else:
            logger.warning("No contact attachment in AWAITING_CONTACT event for user %s", user_id)

    # Scenario 04: generate invite deep link for new seller
    @dp.message_created(F.message.body.text == ADD_SELLER_BTN_TEXT)
    async def on_add_seller_btn(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        route: str = "registration",
    ):
        if route != "staff" or staff is None or not staff.is_owner:
            return
        token = make_invite_token(staff.max_user_id)
        link = staff_invite_deeplink(token)
        await event.message.answer(
            f"Перешлите это сообщение продавцу, которого хотите добавить. "
            f"Ссылка действует сегодня и завтра.\n\n{link}"
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
            await event.message.answer(
                f"👤 {name}",
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
        await event.message.answer(
            "Пришлите номер клиента",
            attachments=[cancel_keyboard("find_customer:cancel")],
        )


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
