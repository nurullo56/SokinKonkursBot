import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import Config
from database.connection import Database
from database.models import init_db
from handlers import admin_router, user_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _bootstrap_settings(db: Database) -> None:
    """Seed BOT_TOKEN and ADMIN_IDS from environment if not already in the DB."""
    env_token = os.getenv("BOT_TOKEN", "").strip()
    if env_token and not await db.get_setting("bot_token"):
        await db.set_setting("bot_token", env_token)
        logger.info("BOT_TOKEN loaded from environment.")

    env_admins = os.getenv("ADMIN_IDS", "").strip()
    if env_admins:
        await db.set_setting("admin_ids", env_admins)
        logger.info("ADMIN_IDS loaded from environment: %s", env_admins)


async def _setup_commands(bot: Bot, admin_ids: list[int]) -> None:
    user_commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
    ]
    admin_commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="admin", description="Admin panel"),
    ]

    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning("Could not set commands for admin %s: %s", admin_id, e)


async def main() -> None:
    config = Config()
    db = Database(config.db_path)
    await db.connect()
    await init_db(db)
    await _bootstrap_settings(db)

    token = await db.get_setting("bot_token")
    if not token:
        logger.error(
            "BOT_TOKEN is not configured. "
            "Set the BOT_TOKEN environment variable or insert it into the settings table."
        )
        await db.disconnect()
        return

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    bot_info = await bot.get_me()
    bot_username: str = bot_info.username

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        storage = RedisStorage.from_url(redis_url)
        logger.info("RedisStorage connected: %s", redis_url)
    except Exception as e:
        logger.warning("Redis ulanmadi, MemoryStorage ishlatiladi: %s", e)
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)
    dp["db"] = db
    dp["bot_username"] = bot_username

    dp.include_router(user_router)
    dp.include_router(admin_router)

    admin_ids_str = await db.get_setting("admin_ids") or ""
    admin_ids = [
        int(x.strip()) for x in admin_ids_str.split(",") if x.strip().lstrip("-").isdigit()
    ]
    await _setup_commands(bot, admin_ids)

    webhook_host = os.getenv("WEBHOOK_HOST", "").strip().rstrip("/")

    if webhook_host:
        webhook_path = f"/webhook/{token}"
        webhook_url = f"{webhook_host}{webhook_path}"
        port = int(os.getenv("WEBHOOK_PORT", "8080"))

        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query", "chat_join_request"],
            drop_pending_updates=True,
        )
        logger.info("Webhook set: %s", webhook_url)

        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()

        logger.info("Bot @%s webhook mode, port %s", bot_username, port)
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
            await bot.delete_webhook()
            await db.disconnect()
            await bot.session.close()
    else:
        logger.info("Bot @%s polling mode", bot_username)
        try:
            await dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_join_request"])
        finally:
            await db.disconnect()
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
