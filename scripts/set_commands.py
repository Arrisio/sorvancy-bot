"""Register default bot commands via Max API."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from maxapi import Bot
from maxapi.types.command import BotCommand

load_dotenv()


async def main():
    token = os.environ["BOT_TOKEN"]
    bot = Bot(token)
    try:
        result = await bot.set_my_commands(
            BotCommand(name="start", description="Начать работу с ботом"),
        )
        print(f"Commands set. Bot: {result.first_name} (@{result.username})")
        for cmd in result.commands or []:
            print(f"  /{cmd.name} — {cmd.description}")
    finally:
        await bot.close_session()


if __name__ == "__main__":
    asyncio.run(main())
