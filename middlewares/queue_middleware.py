import asyncio
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class QueueMiddleware(BaseMiddleware):
    """
    Har bir user uchun bitta so'rov bir vaqtda ishlanadi.
    Agar oldingi so'rov hali tugamagan bo'lsa — yangi so'rov o'tkazib yuboriladi.
    Global semaphore bot yuklanishini cheklaydi.
    """

    def __init__(self, max_concurrent: int = 20) -> None:
        self._global = asyncio.Semaphore(max_concurrent)
        self._user_locks: dict[int, asyncio.Lock] = {}

    def _get_lock(self, user_id: int) -> asyncio.Lock:
        # setdefault — CPython da atomic, race condition yo'q
        return self._user_locks.setdefault(user_id, asyncio.Lock())

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id: int | None = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None

        if user_id is None:
            return await handler(event, data)

        lock = self._get_lock(user_id)

        if lock.locked():
            # User ning oldingi so'rovi hali ishlanmoqda — o'tkazib yuboramiz
            if isinstance(event, CallbackQuery):
                await event.answer()
            return

        async with self._global:
            async with lock:
                return await handler(event, data)
        # Lock bo'shatilgandan keyin, hech kim kutmayotgan bo'lsa o'chiramiz
        if not getattr(lock, "_waiters", None):
            self._user_locks.pop(user_id, None)
