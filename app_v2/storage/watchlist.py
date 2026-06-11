import json
import os
import logging
from storage.database import get_db

log = logging.getLogger("torrent_bot")

_JSON_PATH = "/app/app_v2/storage/watchlist.json"

async def _migrate():
    if not os.path.exists(_JSON_PATH):
        return
    try:
        with open(_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return
        async with get_db() as db:
            for hash_id, info in data.items():
                await db.execute(
                    "INSERT OR IGNORE INTO watchlist (hash_id, uid, title, size) VALUES (?, ?, ?, ?)",
                    (hash_id.lower(), info.get("uid"), info.get("title", ""), info.get("size", 0))
                )
            await db.commit()
        os.rename(_JSON_PATH, _JSON_PATH + ".migrated")
        log.info(f"[WATCHLIST] Migrated {len(data)} entries from JSON")
    except Exception as e:
        log.error(f"[WATCHLIST] Migration error: {e}")

async def init_watchlist():
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                hash_id TEXT PRIMARY KEY,
                uid INTEGER,
                title TEXT,
                size INTEGER DEFAULT 0
            )
        """)
        await db.commit()
    await _migrate()

async def add_watch(hash_id: str, uid: int, title: str, size: int = 0):
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO watchlist (hash_id, uid, title, size) VALUES (?, ?, ?, ?)",
            (hash_id.lower(), uid, title, size)
        )
        await db.commit()

async def remove_watch(hash_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM watchlist WHERE hash_id = ?", (hash_id.lower(),))
        await db.commit()

async def update_size(hash_id: str, size: int):
    async with get_db() as db:
        await db.execute("UPDATE watchlist SET size = ? WHERE hash_id = ?", (size, hash_id.lower()))
        await db.commit()

async def get_watch(hash_id: str):
    async with get_db() as db:
        async with db.execute("SELECT * FROM watchlist WHERE hash_id = ?", (hash_id.lower(),)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_all_watches() -> dict:
    async with get_db() as db:
        async with db.execute("SELECT * FROM watchlist") as cur:
            rows = await cur.fetchall()
            return {row["hash_id"]: dict(row) for row in rows}
