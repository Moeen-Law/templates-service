import logging
import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.models.base import Base

logger = logging.getLogger(__name__)

settings = get_settings()
_engine_kwargs: dict[str, object] = {"echo": False}
if os.getenv("PYTEST_CURRENT_TEST") is not None:
    _engine_kwargs["poolclass"] = NullPool

engine: AsyncEngine = create_async_engine(settings.database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    logger.debug("Opening database session")
    async with SessionLocal() as session:
        yield session
    logger.debug("Database session closed")


async def init_db() -> None:
    logger.info("Initializing database schema")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialization completed")
