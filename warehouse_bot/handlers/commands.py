"""Обработчики базовых команд бота."""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from warehouse_bot.services import product_service

# Создаем "роутер" для наших хендлеров.
router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """
    Обработчик команды /start.
    """
    await message.answer("Привет! Я складской бот. Чем могу помочь?")


@router.message(Command(commands=["list"]))
async def handle_list_products(message: Message, session: AsyncSession) -> None:
    """
    Обработчик команды /list.
    Показывает список всех товаров на складе.

    Args:
        message: Объект сообщения от пользователя.
        session: Сессия базы данных (передается через middleware).
    """
    try:
        products = await product_service.get_all_products(session)

        if not products:
            await message.answer("Склад пуст.")
            return

        # Формируем красивый ответ
        response_lines = ["Список товаров на складе:"]
        for product in products:
            response_lines.append(f"- {product.name}: {product.quantity} шт.")

        await message.answer("\n".join(response_lines))

    except Exception:
        # 🛡️ Логируем полную информацию об ошибке
        logging.exception("Произошла ошибка в хендлере handle_list_products")
        # 🗣️ Сообщаем пользователю, что что-то пошло не так
        await message.answer("Произошла внутренняя ошибка. Попробуйте позже.")
