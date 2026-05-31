import logging

from database.connection import Database

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Add referral. Returns True on success, False if duplicate or self-referral."""
        if referrer_id == referred_id:
            return False
        try:
            # INSERT OR IGNORE — UNIQUE(referred_id) constraint atomik ravishda
            # race condition ni oldini oladi: SELECT+INSERT emas, bitta operatsiya
            result = await self.db.execute(
                "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                (referrer_id, referred_id),
            )
            if result.rowcount == 0:
                return False
            await self.db.execute(
                "UPDATE users SET referral_count = referral_count + 1, "
                "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (referrer_id,),
            )
            await self.db.commit()
            return True
        except Exception:
            logger.exception("add_referral failed referrer=%s referred=%s", referrer_id, referred_id)
            return False

    async def get_referral_count(self, user_id: int) -> int:
        row = await self.db.fetchone(
            "SELECT referral_count FROM users WHERE user_id = ?", (user_id,)
        )
        return row["referral_count"] if row else 0

    async def get_referred_users(self, user_id: int) -> list[int]:
        rows = await self.db.fetchall(
            "SELECT referred_id FROM referrals WHERE referrer_id = ? ORDER BY created_at",
            (user_id,),
        )
        return [r["referred_id"] for r in rows]
