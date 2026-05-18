import asyncio
import logging

from maxapi import Bot, Dispatcher

import config
from src.db.connection import get_engine, close_engine
from src.middleware import RoutingMiddleware
from src.handlers.mode import register_mode_handlers
from src.handlers.start import register_start_handlers
from src.handlers.registration import register_registration_handlers
from src.handlers.profile import register_profile_handlers
from src.handlers.staff import register_staff_handlers
from src.handlers.broadcast import register_broadcast_handlers
from src.handlers.excel import register_excel_handlers
from src.handlers.text_router import register_text_router
from src.handlers.callback_router import register_callback_router
from src.scheduler import broadcast_delivery_loop, birthday_reminder_loop, coupon_expiry_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(config.BOT_TOKEN)
    dp = Dispatcher()

    get_engine()
    logger.info("DB engine initialized")

    # Middleware: injects staff/customer/route into every handler
    dp.middlewares.append(RoutingMiddleware())

    # /mode intercepted first regardless of customer_mode (per spec)
    await register_mode_handlers(dp)

    # Exact-match reply keyboard buttons (registered before generic text catcher)
    await register_start_handlers(dp)
    await register_registration_handlers(dp)
    await register_profile_handlers(dp)
    await register_staff_handlers(dp)
    await register_broadcast_handlers(dp)
    await register_excel_handlers(dp)

    # Generic text — must come AFTER all exact-text handlers
    await register_text_router(dp)

    # Single unified callback router — handles all message_callback events
    await register_callback_router(dp)

    asyncio.create_task(broadcast_delivery_loop(bot))
    asyncio.create_task(birthday_reminder_loop(bot))
    asyncio.create_task(coupon_expiry_loop())

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await bot.close_session()
        await close_engine()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
