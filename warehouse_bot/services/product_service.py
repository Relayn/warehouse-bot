"""Сервисный слой для управления товарами."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from warehouse_bot.db.models import Product


async def create_product(session: AsyncSession, name: str, quantity: int) -> Product:
    """
    Создает новый товар в базе данных.

    Args:
        session: Сессия базы данных.
        name: Название товара.
        quantity: Начальное количество товара.

    Returns:
        Созданный объект товара.
    """
    db_product = Product(name=name, quantity=quantity)
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)
    return db_product


async def get_all_products(session: AsyncSession) -> Sequence[Product]:
    """
    Возвращает список всех товаров.

    Args:
        session: Сессия базы данных.

    Returns:
        Последовательность объектов Product.
    """
    statement = select(Product).order_by(Product.name)
    # ИСПРАВЛЕНО: .exec() заменен на .execute()
    result = await session.execute(statement)
    return result.scalars().all()


async def get_product_by_name(session: AsyncSession, name: str) -> Product | None:
    """
    Находит товар по его уникальному имени.

    Args:
        session: Сессия базы данных.
        name: Название товара для поиска.

    Returns:
        Объект Product или None, если товар не найден.
    """
    statement = select(Product).where(Product.name == name)
    # ИСПРАВЛЕНО: .exec() заменен на .execute()
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def update_product_quantity(
    session: AsyncSession, product_id: int, quantity_change: int
) -> Product:
    """
    Обновляет количество товара, обеспечивая атомарность.

    Args:
        session: Сессия базы данных.
        product_id: ID товара для обновления.
        quantity_change: Изменение количества (может быть положительным или
                         отрицательным).

    Returns:
        Обновленный объект Product.

    Raises:
        ValueError: Если товар не найден или если итоговое количество
                    становится отрицательным.
    """
    db_product = await session.get(Product, product_id)
    if not db_product:
        raise ValueError(f"Товар с ID {product_id} не найден.")

    if db_product.quantity + quantity_change < 0:
        raise ValueError("Недостаточно товара на складе для списания.")

    db_product.quantity += quantity_change
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)

    return db_product
