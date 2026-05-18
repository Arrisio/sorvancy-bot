"""
Single unified handler for all message_callback events.
Routes to sub-handlers based on `route`, `staff`, and FSM state.
"""
import logging

from maxapi.types import MessageCallback
from maxapi.context import MemoryContext

from src.db.orm import Customer, Staff
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.handlers.callbacks.survey import handle_survey_callback
from src.handlers.callbacks.profile import handle_profile_callback
from src.handlers.callbacks.staff_cb import handle_staff_callback

logger = logging.getLogger(__name__)


async def register_callback_router(dp):

    @dp.message_callback()
    async def unified_callback_handler(
        event: MessageCallback,
        context: MemoryContext,
        route: str = "registration",
        customer: Customer | None = None,
        staff: Staff | None = None,
    ):
        payload = event.callback.payload
        user_id = event.callback.user.user_id
        state = await context.get_state()

        await event.bot.send_callback(
            callback_id=event.callback.callback_id, notification="Принято"
        )

        if route == "staff" and staff is not None:
            await handle_staff_callback(event, context, staff, state, payload, user_id)
            return

        bot = event.bot

        async def get_customer():
            nonlocal customer
            if customer is None:
                async with get_session_factory()() as session:
                    customer = await customer_model.get_by_max_id(session, user_id)
            return customer

        if not await handle_survey_callback(bot, user_id, state, payload, context):
            await handle_profile_callback(bot, user_id, state, payload, context, get_customer, event)
