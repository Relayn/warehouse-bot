"""Обработчики для FSM-сценариев управления товарами."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from warehouse_bot.fsm.product_states import ProductState
from warehouse_bot.services import product_service

router = Router()


# --- Универсальный отменщик FSM ---
@router.message(Command(commands=["cancel"]))
@router.message(F.text.casefold() == "отмена")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """
    Позволяет пользователю отменить любое действие FSM.
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активных действий для отмены.")
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer("Действие отменено.")


# --- Сценарий добавления товара ---
@router.message(Command(commands=["add"]))
async def handle_add_product_start(message: Message, state: FSMContext) -> None:
    """
    Начало сценария добавления товара.
    """
    await state.set_state(ProductState.add_waiting_for_name)
    await message.answer("Введите название нового товара:")


@router.message(ProductState.add_waiting_for_name)
async def process_add_product_name(message: Message, state: FSMContext) -> None:
    """
    Обработка названия товара и запрос количества.
    """
    if not message.text:
        await message.answer("Название не может быть пустым. Попробуйте еще раз.")
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(ProductState.add_waiting_for_quantity)
    await message.answer("Теперь введите количество (только цифры):")


@router.message(ProductState.add_waiting_for_quantity)
async def process_add_product_quantity(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """
    Обработка количества и создание/обновление товара.
    """
    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректное число.")
        return

    quantity = int(message.text)
    if quantity <= 0:
        await message.answer("Количество должно быть больше нуля.")
        return

    user_data = await state.get_data()
    product_name = user_data["name"]

    try:
        existing_product = await product_service.get_product_by_name(
            session, product_name
        )
        if existing_product and existing_product.id:
            updated_product = await product_service.update_product_quantity(
                session, existing_product.id, quantity
            )
            await message.answer(
                f"Количество товара '{updated_product.name}' "
                f"увеличено на {quantity}. "
                f"Новый остаток: {updated_product.quantity} шт."
            )
        else:
            new_product = await product_service.create_product(
                session, name=product_name, quantity=quantity
            )
            await message.answer(
                f"Новый товар '{new_product.name}' "
                f"успешно добавлен в количестве {new_product.quantity} шт."
            )
    except IntegrityError:
        logging.warning("Race condition prevented for product: %s", product_name)
        await message.answer(
            "Произошла ошибка конкурентного доступа. Попробуйте еще раз."
        )
    except Exception:
        logging.exception("Error in process_add_product_quantity")
        await message.answer("Произошла внутренняя ошибка. Попробуйте позже.")
    finally:
        await state.clear()


# --- Сценарий списания товара ---
@router.message(Command(commands=["remove"]))
async def handle_remove_product_start(message: Message, state: FSMContext) -> None:
    """
    Начало сценария списания товара.
    """
    await state.set_state(ProductState.remove_waiting_for_name)
    await message.answer("Введите название товара для списания:")


@router.message(ProductState.remove_waiting_for_name)
async def process_remove_product_name(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """
    Проверка наличия товара и запрос количества для списания.
    """
    if not message.text:
        await message.answer("Название не может быть пустым. Попробуйте еще раз.")
        return

    product_name = message.text.strip()
    product = await product_service.get_product_by_name(session, product_name)

    if not product or not product.id:
        await message.answer(
            f"Товар с названием '{product_name}' не найден. "
            "Проверьте список товаров командой /list."
        )
        await state.clear()
        return

    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(ProductState.remove_waiting_for_quantity)
    await message.answer(
        f"Товар '{product.name}' (остаток: {product.quantity} шт.).\n"
        "Сколько единиц списать?"
    )


@router.message(ProductState.remove_waiting_for_quantity)
async def process_remove_product_quantity(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """
    Обработка количества для списания и обновление товара.
    """
    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректное число.")
        return

    quantity_to_remove = int(message.text)
    if quantity_to_remove <= 0:
        await message.answer("Количество для списания должно быть больше нуля.")
        return

    user_data = await state.get_data()
    product_id = user_data["product_id"]
    product_name = user_data["product_name"]

    try:
        updated_product = await product_service.update_product_quantity(
            session, product_id, -quantity_to_remove
        )
        await message.answer(
            f"Со склада списано {quantity_to_remove} шт. товара '{product_name}'.\n"
            f"Новый остаток: {updated_product.quantity} шт."
        )
    except ValueError as e:
        await message.answer(str(e))
    except Exception:
        logging.exception("Error in process_remove_product_quantity")
        await message.answer("Произошла внутренняя ошибка. Попробуйте позже.")
    finally:
        await state.clear()
