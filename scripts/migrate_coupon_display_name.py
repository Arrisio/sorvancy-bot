"""
Migration: add display_name to coupons; add coupon_display_name to broadcasts.

Safe to run multiple times — skips columns that already exist.

Run:
    python scripts/migrate_coupon_display_name.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import config


def _db_url() -> str:
    return (
        f"postgresql+asyncpg://{config.DB_USER}:{config.DB_PASSWORD}"
        f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )


async def _column_exists(conn, table: str, column: str) -> bool:
    result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.fetchone() is not None


async def main():
    engine = create_async_engine(_db_url())
    try:
        async with engine.begin() as conn:

            # --- coupons.display_name ---
            if await _column_exists(conn, "coupons", "display_name"):
                print("coupons.display_name already exists — skipping.")
            else:
                await conn.execute(text("ALTER TABLE coupons ADD COLUMN display_name TEXT"))
                await conn.execute(
                    text("""
                        UPDATE coupons SET display_name = CASE
                            WHEN type = 'anket'
                                THEN 'Бонус ' || value || ' ₽ до ' || to_char(valid_until AT TIME ZONE 'UTC', 'DD.MM.YY')
                            WHEN type = 'birthday'
                                THEN 'ДР: ' || value || ' ₽ до ' || to_char(valid_until AT TIME ZONE 'UTC', 'DD.MM.YY')
                            ELSE value || ' ₽ до ' || to_char(valid_until AT TIME ZONE 'UTC', 'DD.MM.YY')
                        END
                    """)
                )
                await conn.execute(
                    text("ALTER TABLE coupons ALTER COLUMN display_name SET NOT NULL")
                )
                print("coupons.display_name: added and backfilled.")

            # --- broadcasts.coupon_display_name ---
            if await _column_exists(conn, "broadcasts", "coupon_display_name"):
                print("broadcasts.coupon_display_name already exists — skipping.")
            else:
                await conn.execute(
                    text("ALTER TABLE broadcasts ADD COLUMN coupon_display_name TEXT")
                )
                print("broadcasts.coupon_display_name: added.")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
