"""Состояния (FSM) для управления товарами."""

from aiogram.fsm.state import State, StatesGroup


class ProductState(StatesGroup):
    """
    Состояния для сценария добавления/списания товара.
    """

    # Состояния для добавления
    add_waiting_for_name = State()
    add_waiting_for_quantity = State()

    # Состояния для списания
    remove_waiting_for_name = State()
    remove_waiting_for_quantity = State()
