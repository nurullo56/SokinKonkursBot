import aiosqlite
import random
from typing import Optional

from database.connection import Database


class ContestService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def generate_contest_number(self) -> Optional[int]:
        """Pick a random unique number in [100000, 999999]."""
        for _ in range(100):
            number = random.randint(100000, 999999)
            row = await self.db.fetchone(
                "SELECT 1 FROM users WHERE contest_number = ?", (number,)
            )
            if not row:
                return number
        return None

    async def verify_user(self, user_id: int) -> Optional[int]:
        """Assign a unique contest number and mark user as verified. Returns the number."""
        for _ in range(10):
            number = await self.generate_contest_number()
            if number is None:
                return None
            try:
                cursor = await self.db.execute(
                    "UPDATE users SET contest_number = ?, verified = TRUE, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE user_id = ? AND verified = FALSE",
                    (number, user_id),
                )
                await self.db.commit()
                if cursor.rowcount > 0:
                    return number
                # Boshqa coroutine allaqachon verify qilgan — uning raqamini qaytaramiz
                row = await self.db.fetchone(
                    "SELECT contest_number FROM users WHERE user_id = ? AND verified = TRUE",
                    (user_id,),
                )
                if row:
                    return row["contest_number"]
                # verified = FALSE, lekin rowcount = 0 — kutilmagan holat, qayta urinish
                continue
            except aiosqlite.IntegrityError:
                # contest_number UNIQUE collision — boshqa raqam bilan qayta urinish
                continue
            except Exception:
                return None
        return None

    async def is_user_eligible(self, user_id: int) -> bool:
        """True if user has 5+ referrals and is not yet verified."""
        row = await self.db.fetchone(
            "SELECT referral_count, verified FROM users WHERE user_id = ?", (user_id,)
        )
        if not row:
            return False
        return row["referral_count"] >= 5 and not row["verified"]

    async def is_contest_active(self) -> bool:
        value = await self.db.get_setting("contest_active")
        return value == "TRUE"

    async def get_stats(self) -> dict:
        total = await self.db.fetchone(
            "SELECT COUNT(*) AS c FROM users WHERE participated = TRUE"
        )
        verified = await self.db.fetchone(
            "SELECT COUNT(*) AS c FROM users WHERE verified = TRUE"
        )
        pending = await self.db.fetchone(
            "SELECT COUNT(*) AS c FROM users WHERE referral_count >= 5 AND verified = FALSE"
        )
        top = await self.db.fetchall(
            "SELECT user_id, first_name, referral_count FROM users "
            "ORDER BY referral_count DESC LIMIT 5"
        )
        return {
            "total": total["c"] if total else 0,
            "verified": verified["c"] if verified else 0,
            "pending": pending["c"] if pending else 0,
            "top_referrers": top,
        }
