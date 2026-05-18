from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm import FinancialConfig


async def get_or_create(session: AsyncSession) -> FinancialConfig:
    result = await session.execute(select(FinancialConfig).where(FinancialConfig.id == 1))
    cfg = result.scalar_one_or_none()
    if cfg is None:
        cfg = FinancialConfig(id=1)
        session.add(cfg)
        await session.flush()
        await session.refresh(cfg)
    return cfg


async def update_field(session: AsyncSession, **kwargs) -> FinancialConfig:
    await session.execute(
        update(FinancialConfig).where(FinancialConfig.id == 1).values(**kwargs)
    )
    result = await session.execute(select(FinancialConfig).where(FinancialConfig.id == 1))
    return result.scalar_one()
