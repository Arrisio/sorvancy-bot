import logging
from datetime import datetime, timezone
from maxapi.types import BotStarted, MessageCreated, Command
from maxapi.types.input_media import InputMediaBuffer
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import RegistrationState
from src.keyboards import (
    registered_keyboard,
    staff_keyboard,
    superuser_keyboard,
    unregistered_keyboard,
    DISCOUNT_BTN_TEXT,
    CONTACT_STAFF_BTN_TEXT,
)
from src.db.orm import Staff, Customer
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import staff as staff_model
from src.models import coupon as coupon_model
from src.services.discount import make_qr_png, customer_qr_deeplink
from src.services.invite import verify_invite_token
from src.handlers.staff import _send_customer_profile_by_id
from src.handlers.callbacks._common import _display_name

logger = logging.getLogger(__name__)

SHOW_PROFILE_PREFIX = "show_profile_"


async def register_start_handlers(dp):

    @dp.bot_started()
    async def on_bot_started(
        event: BotStarted,
        context: MemoryContext,
        staff: Staff | None = None,
        customer: Customer | None = None,
        route: str = "registration",
    ):
        user_id = event.user.user_id
        username = getattr(event.user, "name", None)

        payload = getattr(event, "payload", None) or getattr(event.user, "start_payload", None)

        # Scenario 04: staff invite deep link
        if payload and isinstance(payload, str) and not payload.startswith(SHOW_PROFILE_PREFIX):
            owner_id, error = verify_invite_token(payload)
            if error == "expired":
                await event.bot.send_message(
                    user_id=user_id,
                    text="Ссылка устарела. Попросите владельца магазина выслать новую.",
                )
                return
            if owner_id is not None:
                async with get_session_factory()() as session:
                    existing = await staff_model.get_by_max_id(session, user_id)
                first_name = getattr(event.user, "first_name", None) or getattr(event.user, "name", None)
                last_name = getattr(event.user, "last_name", None)
                name = _display_name(first_name, last_name) or str(user_id)
                if existing:
                    await event.bot.send_message(
                        user_id=user_id,
                        text="Вы уже зарегистрированы как продавец.",
                    )
                    try:
                        await event.bot.send_message(
                            user_id=owner_id,
                            text="Продавец уже зарегистрирован.",
                        )
                    except Exception:
                        logger.warning("Could not notify owner %s of duplicate seller", owner_id)
                    return
                async with get_session_factory()() as session:
                    async with session.begin():
                        await staff_model.create(
                            session,
                            max_user_id=user_id,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            is_owner=False,
                        )
                await event.bot.send_message(
                    user_id=user_id,
                    text="Вы зарегистрированы как продавец магазина «Сорванцы».",
                    attachments=[staff_keyboard()],
                )
                try:
                    await event.bot.send_message(
                        user_id=owner_id,
                        text=f"Продавец {name} зарегистрирован.",
                    )
                except Exception:
                    logger.warning("Could not notify owner %s of new seller", owner_id)
                return

        # Deeplink scenario 06: staff scans customer QR → show_profile_<id>
        if payload and isinstance(payload, str) and payload.startswith(SHOW_PROFILE_PREFIX):
            if route == "staff":
                cid_str = payload[len(SHOW_PROFILE_PREFIX):]
                try:
                    cid = int(cid_str)
                except ValueError:
                    pass
                else:
                    await _send_customer_profile_by_id(event.bot, user_id, cid)
                    return

        await _route_start(event.bot, user_id, username, context, staff, customer, route)

    @dp.message_created(Command("start"))
    async def on_start_command(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        customer: Customer | None = None,
        route: str = "registration",
    ):
        sender = event.message.sender
        user_id = sender.user_id
        username = getattr(sender, "name", None)
        await _route_start(event.bot, user_id, username, context, staff, customer, route)

    @dp.message_created(F.message.body.text == DISCOUNT_BTN_TEXT)
    async def on_discount_button(
        event: MessageCreated,
        context: MemoryContext,
        route: str = "registration",
    ):
        await _send_discount_qr(event.bot, event.message.sender.user_id)

    @dp.message_created(F.message.body.text == CONTACT_STAFF_BTN_TEXT)
    async def on_contact_staff(event: MessageCreated, context: MemoryContext):
        user_id = event.message.sender.user_id
        async with get_session_factory()() as session:
            async with session.begin():
                customer = await customer_model.get_by_max_id(session, user_id)
                if customer:
                    await customer_model.update_field(
                        session, customer.id, last_touch=datetime.now(tz=timezone.utc)
                    )
        await event.message.answer("Свяжитесь с нашим магазином: TBD.")


async def _route_start(bot, user_id: int, username: str | None, context: MemoryContext,
                       staff, customer, route: str):
    if route == "staff" and staff is not None:
        state = await context.get_state()
        if state != RegistrationState.REGISTERED:
            await context.set_state(RegistrationState.REGISTERED)
        kb = superuser_keyboard() if staff.is_owner else staff_keyboard()
        name = staff.first_name or "продавец"
        role = "суперпользователь" if staff.is_owner else "продавец"
        await bot.send_message(
            user_id=user_id,
            text=f"С возвращением, {name}! Вы вошли как {role}.",
            attachments=[kb],
        )
        return

    if route == "customer" and customer is not None:
        state = await context.get_state()
        if state != RegistrationState.REGISTERED:
            await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text=(
                f"С возвращением, {customer.first_name or 'покупатель'}!\n"
                f"Ваша скидка {customer.discount_percent}% активна."
            ),
            attachments=[registered_keyboard(
                survey_completed=customer.survey_completed,
                survey_draft=customer.survey_draft,
            )],
        )
        return

    # Registration branch
    await context.clear()
    await context.update_data(max_user_id=user_id, max_username=username)
    await bot.send_message(
        user_id=user_id,
        text=(
            "Добро пожаловать в магазин детской одежды Сорванцы! 👋\n\n"
            "Нажмите кнопку ниже, чтобы зарегистрироваться и получить скидку."
        ),
        attachments=[unregistered_keyboard()],
    )


async def _send_discount_qr(bot, user_id: int):
    async with get_session_factory()() as session:
        customer = await customer_model.get_by_max_id(session, user_id)
        coupons = await coupon_model.get_active_by_customer(session, customer.id) if customer else []
    if not customer:
        await bot.send_message(
            user_id=user_id,
            text="Вы ещё не зарегистрированы. Нажмите кнопку ниже.",
            attachments=[unregistered_keyboard()],
        )
        return
    link = customer_qr_deeplink(customer.id)
    coupon_block = ""
    if coupons:
        shown = coupons[:20]
        def _coupon_line(c) -> str:
            line = f"🎁 {c.display_name}"
            if c.min_purchase_amount and c.min_purchase_amount > 0:
                line += f" (от {c.min_purchase_amount} ₽)"
            return line
        lines = "\n".join(_coupon_line(c) for c in shown)
        tail = f"\n…и ещё {len(coupons) - 20}" if len(coupons) > 20 else ""
        coupon_block = f"\nВаши купоны:\n{lines}{tail}\n"
    text = (
        f"Покажите этот QR-код продавцу\n"
        f"Номер клиента: {customer.id}\n"
        f"Скидка: {customer.discount_percent}%\n"
        f"{coupon_block}\n"
        f"Если QR не считывается — отправьте ссылку:\n{link}"
    )
    try:
        qr_bytes = make_qr_png(customer.id)
        media = InputMediaBuffer(buffer=qr_bytes, filename="discount_qr.png")
        await bot.send_message(user_id=user_id, text=text, attachments=[media, registered_keyboard(
            survey_completed=customer.survey_completed,
            survey_draft=customer.survey_draft,
        )])
    except Exception:
        logger.exception("QR generation failed for user %s", user_id)
        await bot.send_message(user_id=user_id, text=text, attachments=[registered_keyboard(
            survey_completed=customer.survey_completed,
            survey_draft=customer.survey_draft,
        )])
    async with get_session_factory()() as session:
        async with session.begin():
            await customer_model.update_field(
                session, customer.id, last_touch=datetime.now(tz=timezone.utc)
            )
