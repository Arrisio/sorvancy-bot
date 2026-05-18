import logging

from maxapi.context import MemoryContext

from src.db.connection import get_session_factory
from src.models import customer as customer_model

logger = logging.getLogger(__name__)


def _display_name(*parts: str | None) -> str:
    return " ".join(filter(None, parts))


async def _append_step_mid(context: MemoryContext, mid: str) -> None:
    data = await context.get_data()
    mids = list(data.get("step_mids") or [])
    mids.append(mid)
    await context.update_data(step_mids=mids)


async def _delete_step_mids(bot, context: MemoryContext) -> None:
    data = await context.get_data()
    for mid in (data.get("step_mids") or []):
        try:
            await bot.delete_message(message_id=mid)
        except Exception:
            pass
    await context.update_data(step_mids=[])


async def _send_step(bot, user_id: int, context: MemoryContext, text: str, keyboard) -> None:
    sent = await bot.send_message(user_id=user_id, text=text, attachments=[keyboard])
    await _append_step_mid(context, sent.message.body.mid)


async def _persist_survey_draft(context: MemoryContext, user_id: int) -> None:
    data = await context.get_data()
    state = await context.get_state()
    draft = {k: v for k, v in data.items() if k.startswith("draft.") or k == "survey_offer_mid"}
    draft["_state"] = str(state)
    try:
        async with get_session_factory()() as session:
            async with session.begin():
                await customer_model.save_survey_draft(session, user_id, draft)
    except Exception:
        logger.warning("Failed to persist survey draft for user %s", user_id)
