from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from database.connection import Database


class VerificationService:
    def __init__(self, db: Database, bot: Bot) -> None:
        self.db = db
        self.bot = bot

    async def check_user_in_bot(self, user_id: int) -> bool:
        """Returns False if the user has blocked the bot."""
        try:
            await self.bot.send_chat_action(chat_id=user_id, action="typing")
            return True
        except (TelegramForbiddenError, TelegramBadRequest):
            return False
        except Exception:
            return False

    async def check_user_in_channel(self, user_id: int, channel_id: int) -> bool:
        """Returns True if the user is an active member of the channel."""
        try:
            member = await self.bot.get_chat_member(channel_id, user_id)
            return member.status not in ("left", "kicked", "banned")
        except Exception:
            return False
