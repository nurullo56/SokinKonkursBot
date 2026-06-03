from typing import Any, Awaitable, Callable
import time

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.connection import Database
from keyboards.user_kb import get_subscription_keyboard
from services.subscription_service import SubscriptionService


class SubscriptionMiddleware(BaseMiddleware):
    # Class-level cache: {user_id: (is_subscribed, expires_at)}
    _cache: dict[int, tuple[bool, float]] = {}
    _CACHE_TTL = 60.0  # kesh muddati - 60 soniya

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db: Database | None = data.get("db")
        bot: Bot | None = data.get("bot")

        if db is None or bot is None:
            return await handler(event, data)

        from_user = None
        if isinstance(event, (Message, CallbackQuery)):
            from_user = event.from_user

        if from_user is None:
            return await handler(event, data)

        # Admins bypass subscription check
        admin_ids_str = await db.get_setting("admin_ids") or ""
        admin_ids = [
            int(x.strip())
            for x in admin_ids_str.split(",")
            if x.strip().lstrip("-").isdigit()
        ]
        if from_user.id in admin_ids:
            return await handler(event, data)

        # Group/supergroup messages always pass through — only check in private
        if isinstance(event, Message) and event.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await handler(event, data)

        # /start, /id and contact share always pass through
        if isinstance(event, Message):
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)
            if event.text and event.text.startswith("/id"):
                return await handler(event, data)
            if event.contact is not None:
                return await handler(event, data)

        # Always let the "Tekshirish" callback through
        if isinstance(event, CallbackQuery) and event.data == "check_subscription":
            return await handler(event, data)

        # Keshni tekshirish
        user_id = from_user.id
        now = time.time()
        if user_id in self._cache:
            is_sub, expires = self._cache[user_id]
            if now < expires and is_sub:
                return await handler(event, data)

        sub_svc = SubscriptionService(db, bot)
        unsubscribed = await sub_svc.get_unsubscribed(user_id)

        if not unsubscribed:
            # Obuna muvaffaqiyatli o'tgan bo'lsa keshga yozamiz
            self._cache[user_id] = (True, now + self._CACHE_TTL)
            return await handler(event, data)

        # Obunadan chiqqan bo'lsa keshdan o'chirib tashlaymiz
        self._cache.pop(user_id, None)
        text = sub_svc.build_prompt_text(unsubscribed)
        keyboard = get_subscription_keyboard(unsubscribed)

        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            await event.answer("Avval kanallarga obuna bo'ling!", show_alert=True)
            if event.message:
                await event.message.answer(text, reply_markup=keyboard)
