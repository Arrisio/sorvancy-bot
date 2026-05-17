import logging
from collections.abc import Awaitable, Callable
from typing import Any

from maxapi.filters.middleware import BaseMiddleware
from maxapi.types import MessageCreated, MessageCallback, BotStarted

from src.db.connection import get_session_factory
from src.models import staff as staff_model
from src.models import customer as customer_model

logger = logging.getLogger(__name__)


def _extract_user_id(event_object: Any) -> int | None:
    if isinstance(event_object, MessageCreated):
        return getattr(event_object.message.sender, "user_id", None)
    if isinstance(event_object, MessageCallback):
        return getattr(event_object.callback.user, "user_id", None)
    if isinstance(event_object, BotStarted):
        return getattr(event_object.user, "user_id", None)
    return None


class RoutingMiddleware(BaseMiddleware):
    """Injects `staff`, `customer`, `route` into handler context per NFR middleware-routing spec."""

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: dict[str, Any],
    ) -> Any:
        user_id = _extract_user_id(event_object)
        if user_id is None:
            return await handler(event_object, data)

        try:
            async with get_session_factory()() as session:
                staff = await staff_model.get_by_max_id(session, user_id)
                customer = None

                if staff is not None and staff.customer_mode:
                    customer = await customer_model.get_by_max_id(session, user_id)
                elif staff is None:
                    customer = await customer_model.get_by_max_id(session, user_id)
        except Exception:
            logger.exception("Middleware DB lookup failed for user %s", user_id)
            staff = None
            customer = None

        data["staff"] = staff
        data["customer"] = customer

        if staff is not None and not staff.customer_mode:
            data["route"] = "staff"
        elif customer is not None:
            data["route"] = "customer"
        else:
            data["route"] = "registration"

        return await handler(event_object, data)
