"""Настройки конфигурации приложения."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Загружает настройки из файла .env.

    Атрибуты:
        model_config: Конфигурация для Pydantic моделей.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # База данных
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int

    # Telegram Bot
    BOT_TOKEN: str
    # URL, на который будет установлен вебхук (например, https://your.domain)
    BASE_WEBHOOK_URL: str
    # Секретный ключ для проверки подлинности запросов от Telegram
    WEBHOOK_SECRET: str

    @property
    def webhook_url(self) -> str:
        """
        Собирает полный URL для вебхука.

        Returns:
            Полный URL вебхука.
        """
        return f"{self.BASE_WEBHOOK_URL}/telegram/webhook/{self.BOT_TOKEN}"

    @property
    def database_url(self) -> str:
        """
        Собирает строку подключения к PostgreSQL.

        Returns:
            Строка подключения для SQLAlchemy.
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()  # type: ignore[call-arg]
