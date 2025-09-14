"""Тесты для FSM-сценариев управления товарами."""

import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, MessageEntity, Update, User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Импортируем сами функции-хендлеры
from warehouse_bot.fsm.product_states import ProductState
from warehouse_bot.handlers.product_management import (
    cancel_handler,
    handle_add_product_start,
    handle_remove_product_start,
    process_add_product_name,
    process_add_product_quantity,
    process_remove_product_name,
    process_remove_product_quantity,
)
from warehouse_bot.middlewares.db_session import DbSessionMiddleware
from warehouse_bot.services import product_service

# Говорим pytest-asyncio использовать один event loop для всего сеанса
pytestmark = pytest.mark.asyncio(scope="session")

# Константы для тестов
TEST_CHAT = Chat(id=123, type="private")
TEST_USER = User(id=123, is_bot=False, first_name="Test")


@pytest.fixture
def dp(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    """
    Фикстура для создания чистого экземпляра Dispatcher для каждого теста
    с вручную зарегистрированными хендлерами для полной изоляции.
    """
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    # Передаем корректную, типизированную фабрику сессий напрямую в middleware
    dp.update.middleware(DbSessionMiddleware(session_pool=session_factory))

    # Создаем новый роутер и регистрируем хендлеры с ПРАВИЛЬНЫМИ фильтрами
    test_router = Router()
    test_router.message.register(cancel_handler, Command(commands=["cancel"]))
    test_router.message.register(cancel_handler, F.text.casefold() == "отмена")
    test_router.message.register(handle_add_product_start, Command(commands=["add"]))
    test_router.message.register(
        handle_remove_product_start, Command(commands=["remove"])
    )
    test_router.message.register(
        process_add_product_name, ProductState.add_waiting_for_name
    )
    test_router.message.register(
        process_add_product_quantity, ProductState.add_waiting_for_quantity
    )
    test_router.message.register(
        process_remove_product_name, ProductState.remove_waiting_for_name
    )
    test_router.message.register(
        process_remove_product_quantity, ProductState.remove_waiting_for_quantity
    )

    dp.include_router(test_router)
    return dp


async def process_update(dp: Dispatcher, bot: AsyncMock, text: str) -> None:
    """Хелпер для симуляции входящего сообщения."""
    entities = []
    if text.startswith("/"):
        entities.append(MessageEntity(type="bot_command", offset=0, length=len(text)))

    message = Message(
        message_id=1,
        chat=TEST_CHAT,
        from_user=TEST_USER,
        text=text,
        entities=entities,
        date=datetime.datetime.now(datetime.UTC),
    )

    # Патчим метод answer, чтобы он перенаправлял вызов на наш mock bot
    async def mock_answer(self: Message, text: str, **kwargs: Any) -> Message:
        return await bot.send_message(chat_id=self.chat.id, text=text, **kwargs)  # type: ignore[no-any-return]

    with patch.object(Message, "answer", mock_answer):
        update = Update(update_id=1, message=message)
        await dp.feed_update(bot, update)


async def test_add_product_full_scenario(dp: Dispatcher, session: AsyncSession) -> None:
    """Тестирует полный успешный сценарий добавления нового товара."""
    bot = AsyncMock()

    await process_update(dp, bot, "/add")
    bot.send_message.assert_called_with(
        chat_id=TEST_CHAT.id, text="Введите название нового товара:"
    )
    bot.reset_mock()

    await process_update(dp, bot, "Супер-дрель")
    bot.send_message.assert_called_with(
        chat_id=TEST_CHAT.id, text="Теперь введите количество (только цифры):"
    )
    bot.reset_mock()

    await process_update(dp, bot, "50")
    bot.send_message.assert_called_with(
        chat_id=TEST_CHAT.id,
        text="Новый товар 'Супер-дрель' успешно добавлен в количестве 50 шт.",
    )

    product = await product_service.get_product_by_name(session, "Супер-дрель")
    assert product is not None
    assert product.quantity == 50


async def test_remove_product_not_enough_stock(
    dp: Dispatcher, session: AsyncSession
) -> None:
    """Тестирует сценарий списания, когда на складе недостаточно товара."""
    bot = AsyncMock()
    await product_service.create_product(session, "Молоток", 10)

    await process_update(dp, bot, "/remove")
    bot.reset_mock()
    await process_update(dp, bot, "Молоток")
    bot.reset_mock()

    await process_update(dp, bot, "100")
    bot.send_message.assert_called_with(
        chat_id=TEST_CHAT.id, text="Недостаточно товара на складе для списания."
    )

    product = await product_service.get_product_by_name(session, "Молоток")
    assert product is not None
    assert product.quantity == 10
