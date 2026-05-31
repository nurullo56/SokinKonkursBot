
from database.connection import Database

_SQL_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    first_name      TEXT,
    phone           TEXT,
    referral_count  INTEGER DEFAULT 0,
    contest_number  INTEGER UNIQUE,
    participated    BOOLEAN DEFAULT FALSE,
    verified        BOOLEAN DEFAULT FALSE,
    welcomed        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_SQL_REFERRALS = """
CREATE TABLE IF NOT EXISTS referrals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
    FOREIGN KEY (referred_id) REFERENCES users(user_id),
    UNIQUE(referrer_id, referred_id)
)
"""

_SQL_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_SQL_WINNERS = """
CREATE TABLE IF NOT EXISTS winners (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    place          INTEGER NOT NULL,
    contest_number INTEGER NOT NULL,
    announced_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_SQL_PUBLIC_CHANNELS = """
CREATE TABLE IF NOT EXISTS public_channels (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id   TEXT NOT NULL UNIQUE,
    channel_name TEXT,
    channel_link TEXT,
    member_limit INTEGER DEFAULT 0,
    joined_count INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_SQL_ZAYAFKA_CHANNELS = """
CREATE TABLE IF NOT EXISTS zayafka_channels (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id   TEXT NOT NULL UNIQUE,
    channel_name TEXT,
    invite_link  TEXT,
    member_limit INTEGER DEFAULT 0,
    joined_count INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_SQL_ZAYAFKA_REQUESTS = """
CREATE TABLE IF NOT EXISTS zayafka_join_requests (
    user_id    INTEGER NOT NULL,
    channel_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, channel_id)
)
"""

_SQL_CHANNEL_JOINS = """
CREATE TABLE IF NOT EXISTS channel_joins (
    user_id     INTEGER NOT NULL,
    channel_id  TEXT NOT NULL,
    joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, channel_id)
)
"""


async def init_db(db: Database) -> None:
    for sql in (
        _SQL_USERS,
        _SQL_REFERRALS,
        _SQL_SETTINGS,
        _SQL_WINNERS,
        _SQL_PUBLIC_CHANNELS,
        _SQL_ZAYAFKA_CHANNELS,
        _SQL_ZAYAFKA_REQUESTS,
        _SQL_CHANNEL_JOINS,
    ):
        await db.execute(sql)
    
    # Safe migrations for existing databases
    try:
        await db.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE users ADD COLUMN welcomed BOOLEAN DEFAULT FALSE")
    except Exception:
        pass

    for table in ("public_channels", "zayafka_channels"):
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN member_limit INTEGER DEFAULT 0")
        except Exception:
            pass  # Already exists
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN joined_count INTEGER DEFAULT 0")
        except Exception:
            pass  # Already exists

    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)"
    )
    # UNIQUE constraint on referred_id: har bir user faqat bir marta referal bo'lishi mumkin
    # Bu INSERT OR IGNORE + rowcount check bilan race condition ni oldini oladi
    try:
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_referrals_referred_unique ON referrals(referred_id)"
        )
    except Exception:
        pass
    await db.commit()
