import logging
from maxapi.types import MessageCreated, Command
from maxapi.context import MemoryContext

from src.states import RegistrationState
from src.keyboards import superuser_keyboard
from src.db.connection import get_session_factory
from src.models import staff as staff_model
from src.db.orm import Staff

logger = logging.getLogger(__name__)


async def register_mode_handlers(dp):

    @dp.message_created(Command("mode"))
    async def on_mode_command(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
    ):
        user_id = event.message.sender.user_id

        if staff is None or not staff.is_owner:
            return

        new_mode = not staff.customer_mode
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await staff_model.set_customer_mode(session, user_id, new_mode)
        except Exception:
            logger.exception("customer_mode toggle failed for user %s", user_id)
            await event.message.answer("Ошибка при переключении режима.")
            return

        if new_mode:
            await context.set_state(RegistrationState.REGISTERED)
            await event.message.answer(
                "Режим клиента включён. Ваши сообщения обрабатываются как от покупателя."
            )
        else:
            await context.set_state(RegistrationState.REGISTERED)
            await event.message.answer(
                "Режим суперпользователя восстановлен.",
                attachments=[superuser_keyboard()],
            )
