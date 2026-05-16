import logging
from maxapi.types import BotStarted, MessageCreated, MessageCallback, Command
from maxapi.types.input_media import InputMediaBuffer
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import RegistrationState
from src.keyboards import (
    registered_keyboard,
    unregistered_keyboard,
    discount_keyboard,
    SHOW_DISCOUNT_BTN_TEXT,
    MY_PROFILE_BTN_TEXT,
)
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model
from src.services.discount import discount_card, profile_message, make_qr_png

logger = logging.getLogger(__name__)


async def register_start_handlers(dp):

    @dp.bot_started()
    async def on_bot_started(event: BotStarted, context: MemoryContext):
        user = event.user
        await _greet_or_resume(event.bot, user.user_id, getattr(user, "name", None), context)

    @dp.message_created(Command("start"))
    async def on_start_command(event: MessageCreated, context: MemoryContext):
        sender = event.message.sender
        await _greet_or_resume(event.bot, sender.user_id, getattr(sender, "name", None), context)

    @dp.message_created(Command("discount"))
    async def on_discount_command(event: MessageCreated, context: MemoryContext):
        await _send_discount_qr(event.bot, event.message.sender.user_id)

    @dp.message_callback(F.callback.payload == "show_discount")
    async def on_show_discount_callback(event: MessageCallback, context: MemoryContext):
        await event.bot.send_callback(callback_id=event.callback.callback_id, notification="Принято")
        await _send_discount_qr(event.bot, event.callback.user.user_id)

    @dp.message_created(F.message.body.text == SHOW_DISCOUNT_BTN_TEXT)
    async def on_show_discount_button(event: MessageCreated, context: MemoryContext):
        await _send_discount_qr(event.bot, event.message.sender.user_id)

    @dp.message_created(F.message.body.text == MY_PROFILE_BTN_TEXT)
    async def on_profile_button(event: MessageCreated, context: MemoryContext):
        user_id = event.message.sender.user_id
        async with get_session_factory()() as session:
            customer = await customer_model.get_by_max_id(session, user_id)
            children = []
            if customer:
                children = await child_model.get_by_customer(session, customer.id)
        if not customer:
            await event.message.answer(
                "Вы не зарегистрированы.",
                attachments=[unregistered_keyboard()],
            )
            return
        await event.message.answer(
            profile_message(customer, children),
            attachments=[registered_keyboard()],
        )

    @dp.message_created(F.message.body.attachments)
    async def on_attachment(event: MessageCreated, context: MemoryContext):
        logger.info(
            "Attachment from user %s: %s",
            event.message.sender.user_id,
            event.json(),
        )


async def _greet_or_resume(bot, user_id: int, username: str | None, context: MemoryContext):
    async with get_session_factory()() as session:
        customer = await customer_model.get_by_max_id(session, user_id)

    if customer:
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
        qr_bytes = make_qr_png(user_id, customer.discount_percent)
        media = InputMediaBuffer(buffer=qr_bytes, filename="discount_qr.png")
        await bot.send_message(
            user_id=user_id,
            text=f"Ваш код на скидку {customer.discount_percent}%\nПокажите кассиру:",
            attachments=[media],
        )
    except Exception:
        logger.exception("QR generation failed for user %s", user_id)
        await bot.send_message(
            user_id=user_id,
            text=discount_card(customer.first_name or ""),
            attachments=[registered_keyboard()],
        )
