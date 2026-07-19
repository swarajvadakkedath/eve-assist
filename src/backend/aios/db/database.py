"""Database initialization and connection management."""

import os
import aiosqlite
from pathlib import Path


class Database:
    _instance = None

    def __new__(cls, db_path: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str | None = None):
        if not hasattr(self, "_initialized"):
            self._db_path = db_path or str(Path.home() / ".aios" / "aios.db")
            self._conn: aiosqlite.Connection | None = None
            self._initialized = True

    async def connect(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")

    async def disconnect(self):
        if self._conn:
            await self._conn.close()

    async def execute(self, query: str, params: tuple = ()):
        if not self._conn:
            await self.connect()
        return await self._conn.execute(query, params)

    async def fetch_all(self, query: str, params: tuple = ()) -> list:
        cursor = await self.execute(query, params)
        return await cursor.fetchall()

    async def fetch_one(self, query: str, params: tuple = ()):
        cursor = await self.execute(query, params)
        return await cursor.fetchone()

    async def run_migrations(self):
        migrations_dir = Path(__file__).parent / "migrations"
        if migrations_dir.exists():
            for migration_file in sorted(migrations_dir.glob("*.sql")):
                with open(migration_file) as f:
                    await self.execute(f.read())
                await self._conn.commit()
