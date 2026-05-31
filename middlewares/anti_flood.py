import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

_CLEANUP_EVERY = 500  # har 500 xabarda bir marta eski yozuvlar tozalanadi


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 3, window: float = 5.0) -> None:
        self._limit = limit
        self._window = window
        self._timestamps: dict[int, list[float]] = defaultdict(list)
        self._warned: set[int] = set()
        self._call_count = 0

    def _cleanup(self, now: float) -> None:
        """Uzoq vaqt xabar yubormagan foydalanuvchilarni xotiradan o'chirish."""
        stale = [uid for uid, ts in self._timestamps.items() if not ts or now - ts[-1] > self._window * 10]
        for uid in stale:
            del self._timestamps[uid]
            self._warned.discard(uid)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        from_user = event.from_user
        if not from_user:
            return await handler(event, data)

        user_id = from_user.id
        now = time.monotonic()

        self._timestamps[user_id] = [
            t for t in self._timestamps[user_id] if now - t < self._window
        ]
        self._timestamps[user_id].append(now)

        # Vaqti-vaqti bilan idle userlarni tozalash
        self._call_count += 1
        if self._call_count >= _CLEANUP_EVERY:
            self._call_count = 0
            self._cleanup(now)

        if len(self._timestamps[user_id]) > self._limit:
            if user_id not in self._warned:
                self._warned.add(user_id)
                await event.answer(
                    f"⚠️ Juda tez xabar yuboryapsiz. {int(self._window)} soniya kuting."
                )
            return

        self._warned.discard(user_id)
        return await handler(event, data)
