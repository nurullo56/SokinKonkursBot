import aiosqlite
from typing import Optional


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")

    async def disconnect(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _require_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database ulanmagan. connect() ni avval chaqiring.")
        return self._conn

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        return await self._require_connection().execute(query, params)

    async def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        async with await self._require_connection().execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        async with await self._require_connection().execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def commit(self) -> None:
        await self._require_connection().commit()

    async def get_setting(self, key: str) -> Optional[str]:
        row = await self.fetchone(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        return row["value"] if row else None

    async def set_setting(self, key: str, value: str) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) "
            "VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value),
        )
        await self.commit()
