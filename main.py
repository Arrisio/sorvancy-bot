import asyncio
import logging

from maxapi import Bot, Dispatcher

import config
from src.db.connection import get_engine, close_engine
from src.handlers.start import register_start_handlers
from src.handlers.registration import register_registration_handlers

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(config.BOT_TOKEN)
    dp = Dispatcher()

    get_engine()
    logger.info("DB engine initialized")

    await register_start_handlers(dp)
    await register_registration_handlers(dp)

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await close_engine()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
