from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context  # type: ignore[attr-defined]
from warehouse_bot.core.config import settings
from warehouse_bot.db import models  # noqa: F401

# это объект конфигурации Alembic, который предоставляет
# доступ к значениям из используемого .ini файла.
config = context.config

# Интерпретируем файл конфигурации для логгирования Python.
# Эта строка, по сути, настраивает логгеры.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Указываем Alembic на метаданные наших SQLModel моделей
# для поддержки автогенерации миграций.
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# другие значения из конфигурации, определяемые потребностями env.py,
# можно получить так:
# my_important_option = config.get_main_option("my_important_option")
# ... и т.д.


def run_migrations_offline() -> None:
    """Запуск миграций в 'оффлайн' режиме.

    Этот режим конфигурирует контекст только с URL,
    а не с Engine, хотя Engine здесь также допустим.
    Пропуская создание Engine, нам даже не нужно,
    чтобы был доступен DBAPI.

    Вызовы context.execute() здесь выводят заданную строку
    в выходной файл скрипта.
    """
    # Эта строка обновлена: убран вызов .unicode_string()
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Запуск миграций в 'онлайн' режиме.

    В этом сценарии нам нужно создать Engine
    и связать соединение с контекстом.
    """
    # Эта строка обновлена, чтобы использовать наши настройки из .env
    configuration = config.get_section(config.config_ini_section)
    # Эта строка обновлена: убран вызов .unicode_string()
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
