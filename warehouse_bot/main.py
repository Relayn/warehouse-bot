"""Главный файл приложения. Точка входа."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from warehouse_bot.core.config import settings
from warehouse_bot.db.session import AsyncSessionFactory
from warehouse_bot.handlers import commands, product_management
from warehouse_bot.middlewares.db_session import DbSessionMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Контекстный менеджер для управления жизненным циклом приложения.
    """
    print("--- LIFESPAN START ---")

    print("0. Initializing Bot, Dispatcher, Redis connection and FSM storage...")
    bot = Bot(token=settings.BOT_TOKEN)
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    storage = RedisStorage(redis=redis_client)
    dp = Dispatcher(storage=storage)

    # Сохраняем экземпляры в app.state для доступа в хендлерах
    app.state.bot = bot
    app.state.dp = dp
    app.state.redis = redis_client
    print("-> Bot, Dispatcher, Redis and FSM Storage initialized.")

    print("1. Deleting old webhook...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("-> Old webhook deleted.")

    print("2. Registering middlewares and routers...")
    dp.update.middleware(DbSessionMiddleware(session_pool=AsyncSessionFactory))
    dp.include_router(commands.router)
    dp.include_router(product_management.router)
    print("-> Middlewares and routers registered.")

    print(f"3. Setting new webhook to: {settings.webhook_url}")
    await bot.set_webhook(
        url=settings.webhook_url, secret_token=settings.WEBHOOK_SECRET
    )
    print("-> New webhook set successfully.")
    print("--- LIFESPAN STARTUP COMPLETE. APP IS READY. ---")

    yield

    print("--- LIFESPAN SHUTDOWN ---")
    await app.state.bot.delete_webhook()
    await app.state.bot.session.close()
    await app.state.redis.close()
    print("--- LIFESPAN SHUTDOWN COMPLETE ---")


# --- Приложение FastAPI ---
app = FastAPI(lifespan=lifespan)


@app.post("/telegram/webhook/{token}")
async def webhook_handler(request: Request, token: str) -> Response:
    """
    Обработчик вебхуков от Telegram.
    """
    if token != settings.BOT_TOKEN:
        return JSONResponse(content={"error": "Invalid token"}, status_code=403)

    telegram_secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if telegram_secret_token != settings.WEBHOOK_SECRET:
        return JSONResponse(content={"error": "Invalid secret token"}, status_code=403)

    try:
        update = await request.json()
        dp: Dispatcher = request.app.state.dp
        bot: Bot = request.app.state.bot
        await dp.feed_webhook_update(bot=bot, update=update)
    except Exception:
        logging.exception("!!! Critical error in webhook handler !!!")
        return Response(status_code=500)

    return Response(status_code=200)


# --- Точка входа для локального запуска ---
if __name__ == "__main__":
    uvicorn.run(
        "warehouse_bot.main:app",
        host="0.0.0.0",  # noqa: B104
        port=8000,
        reload=True,
    )
