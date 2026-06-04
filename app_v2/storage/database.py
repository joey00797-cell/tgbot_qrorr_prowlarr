import aiosqlite
from contextlib import asynccontextmanager

DATABASE_PATH = "/app/app_v2/storage/bot.db"

@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT,
                status TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                hash_id TEXT PRIMARY KEY,
                uid INTEGER,
                title TEXT,
                tmdb_title TEXT,
                notify TEXT
            )
        """)
        # миграция: добавляем tmdb_title если нет
        try:
            await db.execute("ALTER TABLE downloads ADD COLUMN tmdb_title TEXT DEFAULT ''")
            await db.commit()
        except Exception:
            pass
        await db.commit()
