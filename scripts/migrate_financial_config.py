"""
Migration: add financial_config table and seed singleton row.

Safe to run multiple times — skips if table or row already exists.

Run:
    python scripts/migrate_financial_config.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

import config
from src.db.orm import FinancialConfig


def _db_url() -> str:
    return (
        f"postgresql+asyncpg://{config.DB_USER}:{config.DB_PASSWORD}"
        f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )


_DDL = """
CREATE TABLE IF NOT EXISTS financial_config (
    id                       INTEGER PRIMARY KEY,
    registration_discount_pct INTEGER NOT NULL DEFAULT 10,
    survey_coupon_value       INTEGER NOT NULL DEFAULT 300,
    survey_coupon_valid_days  INTEGER NOT NULL DEFAULT 30,
    survey_coupon_max_pct     INTEGER NOT NULL DEFAULT 30,
    birthday_coupon_value     INTEGER NOT NULL DEFAULT 300,
    birthday_coupon_valid_days INTEGER NOT NULL DEFAULT 7,
    birthday_coupon_max_pct   INTEGER NOT NULL DEFAULT 30
);
"""


async def main():
    engine = create_async_engine(_db_url())
    try:
        async with engine.begin() as conn:
            await conn.execute(text(_DDL))
            print("financial_config table: OK")

        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            existing = await session.scalar(
                select(FinancialConfig).where(FinancialConfig.id == 1)
            )
            if not existing:
                session.add(FinancialConfig(id=1))
                await session.commit()
                print("FinancialConfig row seeded with defaults:")
                print("  registration_discount_pct = 10")
                print("  survey_coupon_value       = 300")
                print("  survey_coupon_valid_days  = 30")
                print("  survey_coupon_max_pct     = 30")
                print("  birthday_coupon_value     = 300")
                print("  birthday_coupon_valid_days = 7")
                print("  birthday_coupon_max_pct   = 30")
            else:
                print("FinancialConfig row already exists — skipping seed.")
                print(f"  registration_discount_pct = {existing.registration_discount_pct}")
                print(f"  survey_coupon_value       = {existing.survey_coupon_value}")
                print(f"  survey_coupon_valid_days  = {existing.survey_coupon_valid_days}")
                print(f"  survey_coupon_max_pct     = {existing.survey_coupon_max_pct}")
                print(f"  birthday_coupon_value     = {existing.birthday_coupon_value}")
                print(f"  birthday_coupon_valid_days = {existing.birthday_coupon_valid_days}")
                print(f"  birthday_coupon_max_pct   = {existing.birthday_coupon_max_pct}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
