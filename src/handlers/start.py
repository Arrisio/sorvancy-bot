import logging
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
from src.services.discount import make_qr_png
from src.services.invite import verify_invite_token

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
                name = " ".join(filter(None, [first_name or "", last_name or ""])) or str(user_id)
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
                    from src.handlers.staff import _send_customer_profile_by_id
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
            attachments=[registered_keyboard()],
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
    if not customer:
        await bot.send_message(
            user_id=user_id,
            text="Вы ещё не зарегистрированы. Нажмите кнопку ниже.",
            attachments=[unregistered_keyboard()],
        )
        return
    try:
        qr_bytes = make_qr_png(customer.id)
        media = InputMediaBuffer(buffer=qr_bytes, filename="discount_qr.png")
        await bot.send_message(
            user_id=user_id,
            text=(
                f"Покажите этот QR-код продавцу\n"
                f"Номер клиента: {customer.id}\n"
                f"Скидка: {customer.discount_percent}%"
            ),
            attachments=[media],
        )
    except Exception:
        logger.exception("QR generation failed for user %s", user_id)
        from src.services.discount import customer_qr_deeplink
        await bot.send_message(
            user_id=user_id,
            text=(
                f"Ваша ссылка для продавца:\n{customer_qr_deeplink(customer.id)}\n"
                f"Номер клиента: {customer.id}\n"
                f"Скидка: {customer.discount_percent}%"
            ),
        )
