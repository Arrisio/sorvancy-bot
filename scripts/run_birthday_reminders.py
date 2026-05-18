import asyncio
from maxapi import Bot
import config
from src.db.connection import get_engine, close_engine
from src.scheduler import _run_birthday_reminders

async def main():
  get_engine()
  bot = Bot(config.BOT_TOKEN)
  try:
      await _run_birthday_reminders(bot)
  finally:
      await bot.close_session()
      await close_engine()

asyncio.run(main())