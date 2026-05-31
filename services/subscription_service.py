import logging

from aiogram import Bot

from database.connection import Database
from utils.emoji import ce

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, db: Database, bot: Bot) -> None:
        self.db = db
        self.bot = bot

    async def get_public_channels(self) -> list[dict]:
        return await self.db.fetchall("SELECT * FROM public_channels ORDER BY id")

    async def get_zayafka_channels(self) -> list[dict]:
        return await self.db.fetchall("SELECT * FROM zayafka_channels ORDER BY id")

    async def _is_member(self, user_id: int, channel_id: str) -> bool:
        # Pass numeric IDs as int — Telegram API works more reliably this way
        try:
            cid: int | str = int(channel_id) if channel_id.lstrip("-").isdigit() else channel_id
            member = await self.bot.get_chat_member(cid, user_id)
            result = member.status not in ("left", "kicked", "banned")
            logger.debug("check_member channel=%s user=%s status=%s → %s", cid, user_id, member.status, result)
            return result
        except Exception as e:
            logger.warning("get_chat_member FAILED channel=%s user=%s → %s", channel_id, user_id, e)
            return False

    async def _has_zayafka_request(self, user_id: int, channel_id: str) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM zayafka_join_requests WHERE user_id = ? AND channel_id = ?",
            (user_id, str(channel_id)),
        )
        return row is not None

    _ALLOWED_TABLES = frozenset({"public_channels", "zayafka_channels"})

    async def _record_channel_join(self, user_id: int, channel_id: str, table_name: str) -> None:
        if table_name not in self._ALLOWED_TABLES:
            logger.error("Invalid table name rejected: %s", table_name)
            return
        # Check if already joined
        row = await self.db.fetchone(
            "SELECT 1 FROM channel_joins WHERE user_id = ? AND channel_id = ?",
            (user_id, str(channel_id)),
        )
        if not row:
            # Insert into joins
            await self.db.execute(
                "INSERT OR IGNORE INTO channel_joins (user_id, channel_id) VALUES (?, ?)",
                (user_id, str(channel_id)),
            )
            # Increment joined_count
            await self.db.execute(
                f"UPDATE {table_name} SET joined_count = joined_count + 1 WHERE channel_id = ?",
                (str(channel_id),),
            )
            await self.db.commit()
            
            # Fetch updated counts to check limit
            ch_data = await self.db.fetchone(
                f"SELECT member_limit, joined_count FROM {table_name} WHERE channel_id = ?",
                (str(channel_id),),
            )
            if ch_data:
                limit = ch_data.get("member_limit", 0) or 0
                joined = ch_data.get("joined_count", 0) or 0
                if limit > 0 and joined >= limit:
                    logger.info("Channel %s reached subscriber limit (%d/%d). Auto-disconnecting...", channel_id, joined, limit)
                    await self.remove_channel(channel_id)

    async def get_unsubscribed(self, user_id: int) -> list[dict]:
        result: list[dict] = []

        # Get list of current public channels first
        public_channels = await self.get_public_channels()
        for ch in public_channels:
            if await self._is_member(user_id, ch["channel_id"]):
                await self._record_channel_join(user_id, ch["channel_id"], "public_channels")
            else:
                result.append({
                    "name": ch["channel_name"] or ch["channel_id"],
                    "link": ch.get("channel_link") or "",
                    "type": "public",
                })

        # Get list of current zayafka channels
        zayafka_channels = await self.get_zayafka_channels()
        for ch in zayafka_channels:
            is_member = await self._is_member(user_id, ch["channel_id"])
            has_request = await self._has_zayafka_request(user_id, ch["channel_id"])
            if is_member or has_request:
                await self._record_channel_join(user_id, ch["channel_id"], "zayafka_channels")
            else:
                result.append({
                    "name": ch["channel_name"] or ch["channel_id"],
                    "link": ch.get("invite_link") or "",
                    "type": "zayafka",
                    "channel_id": ch["channel_id"],
                })

        return result

    async def is_subscribed_all(self, user_id: int) -> bool:
        return len(await self.get_unsubscribed(user_id)) == 0

    def build_prompt_text(self, unsubscribed: list[dict]) -> str:
        return f"{ce('🔔')} Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:"

    # ── Admin helpers ────────────────────────────────────────────────────────

    async def add_public_channel(self, channel_id: str, channel_name: str, channel_link: str, member_limit: int = 0) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO public_channels (channel_id, channel_name, channel_link, member_limit, joined_count) "
            "VALUES (?, ?, ?, ?, COALESCE((SELECT joined_count FROM public_channels WHERE channel_id = ?), 0))",
            (channel_id, channel_name, channel_link, member_limit, channel_id),
        )
        await self.db.commit()

    async def add_zayafka_channel(self, channel_id: str, channel_name: str, invite_link: str, member_limit: int = 0) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO zayafka_channels (channel_id, channel_name, invite_link, member_limit, joined_count) "
            "VALUES (?, ?, ?, ?, COALESCE((SELECT joined_count FROM zayafka_channels WHERE channel_id = ?), 0))",
            (channel_id, channel_name, invite_link, member_limit, channel_id),
        )
        await self.db.commit()

    async def remove_public_channel(self, channel_id: str) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM public_channels WHERE channel_id = ?", (channel_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def remove_zayafka_channel(self, channel_id: str) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM zayafka_channels WHERE channel_id = ?", (channel_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def remove_channel(self, channel_id: str) -> bool:
        r1 = await self.remove_public_channel(channel_id)
        r2 = await self.remove_zayafka_channel(channel_id)
        return r1 or r2
