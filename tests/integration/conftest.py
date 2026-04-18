import asyncio

import pytest

from app.core.db import engine
from app.models.base import Base


@pytest.fixture(autouse=True)
def reset_database() -> None:
    async def _reset() -> None:
        await engine.dispose()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_reset())
