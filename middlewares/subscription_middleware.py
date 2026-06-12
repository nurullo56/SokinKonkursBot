from typing import Any, Awaitable, Callable
import time

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.connection import Database
from keyboards.user_kb import get_subscription_keyboard
from services.subscription_service import SubscriptionService


class SubscriptionMiddleware(BaseMiddleware):
    # Class-level cache: {user_id: (unsubscribed_list, expires_at)}
    # Bo'sh ro'yxat = obuna bo'lgan. Musbat ham, manfiy ham keshlanadi.
    _cache: dict[int, tuple[list[dict], float]] = {}
    _CACHE_TTL = 60.0       # obuna bo'lganlar uchun
    _NEG_CACHE_TTL = 15.0   # obuna bo'lmaganlar — qisqaroq, tez qayta tekshirish uchun

    @classmethod
    def invalidate(cls, user_id: int) -> None:
        """Foydalanuvchi holati o'zgarganda (masalan obuna bo'lgach) keshni tozalash."""
        cls._cache.pop(user_id, None)

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

        # Keshni tekshirish (musbat va manfiy holat ikkalasi ham keshlanadi)
        sub_svc = SubscriptionService(db, bot)
        user_id = from_user.id
        now = time.time()

        cached = self._cache.get(user_id)
        if cached is not None and now < cached[1]:
            unsubscribed = cached[0]
        else:
            unsubscribed = await sub_svc.get_unsubscribed(user_id)
            ttl = self._CACHE_TTL if not unsubscribed else self._NEG_CACHE_TTL
            self._cache[user_id] = (unsubscribed, now + ttl)

        if not unsubscribed:
            return await handler(event, data)

        text = sub_svc.build_prompt_text(unsubscribed)
        keyboard = get_subscription_keyboard(unsubscribed)

        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            await event.answer("Avval kanallarga obuna bo'ling!", show_alert=True)
            if event.message:
                await event.message.answer(text, reply_markup=keyboard)
