from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.connection import Database


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db: Database | None = data.get("db")
        if db is None:
            return

        admin_ids_str = await db.get_setting("admin_ids")
        admin_ids: list[int] = []
        if admin_ids_str:
            admin_ids = [
                int(x.strip())
                for x in admin_ids_str.split(",")
                if x.strip().lstrip("-").isdigit()
            ]

        from_user = None
        if isinstance(event, (Message, CallbackQuery)):
            from_user = event.from_user

        if from_user is None or from_user.id not in admin_ids:
            return

        return await handler(event, data)
