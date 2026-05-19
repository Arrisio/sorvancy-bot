"""
Error alerting via Max messenger.
Sends exception tracebacks to SUPPORT_ID with deduplication and rate limiting.

Call alerts.init(bot) once at startup, then send_error_alert(exc) anywhere.
"""
import asyncio
import hashlib
import logging
import traceback
from collections import defaultdict
from datetime import datetime, UTC

import config

logger = logging.getLogger(__name__)

ERROR_COOLDOWN = 300  # seconds between alerts for same error signature
_last_sent: dict[str, float] = defaultdict(float)
_lock = asyncio.Lock()
_bot = None


def init(bot) -> None:
    global _bot
    _bot = bot


def _signature(exc: BaseException) -> str:
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    raw = "".join(tb[-3:])
    return hashlib.md5(raw.encode()).hexdigest()


async def send_error_alert(exc: BaseException, context: str = "") -> None:
    if _bot is None or config.SUPPORT_ID is None:
        return

    sig = _signature(exc)
    now = asyncio.get_event_loop().time()

    async with _lock:
        if now - _last_sent[sig] < ERROR_COOLDOWN:
            return
        _last_sent[sig] = now

    tb_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = f"ERROR {ts}"
    if context:
        text += f"\n{context}"
    text += f"\n\n{tb_text[-3500:]}"

    try:
        await _bot.send_message(user_id=config.SUPPORT_ID, text=text)
    except Exception:
        logger.exception("Failed to send error alert")


def setup_global_error_handler(loop: asyncio.AbstractEventLoop) -> None:
    def handle_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exc = context.get("exception")
        if exc is None:
            return
        asyncio.create_task(
            send_error_alert(exc, context=context.get("message", ""))
        )

    loop.set_exception_handler(handle_exception)
