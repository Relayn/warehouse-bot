"""Настройка сессии базы данных."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from warehouse_bot.core.config import settings

# Создаем асинхронный "движок" для SQLAlchemy
# Он будет управлять подключениями к базе данных.
async_engine = create_async_engine(
    settings.database_url,
    echo=False,  # В production лучше выключить, чтобы не логировать все SQL-запросы
    pool_pre_ping=True,  # Проверяет "живо" ли соединение перед использованием
)

# Создаем фабрику асинхронных сессий
# Эта фабрика будет создавать новые сессии по запросу.
AsyncSessionFactory = async_sessionmaker(
    async_engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость (dependency) для получения сессии базы данных.

    Yields:
        Объект асинхронной сессии SQLAlchemy.
    """
    async with AsyncSessionFactory() as session:
        yield session
