"""Модели базы данных проекта."""

import datetime

from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    """Модель товара на складе."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100)
    quantity: int = Field(default=0)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
