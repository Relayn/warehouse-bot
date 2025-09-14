"""Конфигурация и фикстуры для тестов Pytest."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

# Используем асинхронный драйвер для SQLite для тестов
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Фикстура для создания асинхронного движка БД для тестов.
    """
    async_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield async_engine

    await async_engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Фикстура, создающая фабрику сессий для тестов.
    """
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Фикстура, предоставляющая изолированную сессию БД для каждого теста.
    """
    async with session_factory() as db_session:
        yield db_session
