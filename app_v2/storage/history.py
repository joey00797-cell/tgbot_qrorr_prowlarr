import json
import os
import logging
from storage.database import get_db

log = logging.getLogger("torrent_bot")

_JSON_PATH = "/app/app_v2/storage/history.json"
_MAX = 50

async def init_history():
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER NOT NULL,
                query TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_history_uid ON history (uid, created_at DESC)")
        await db.commit()
    await _migrate()

async def _migrate():
    if not os.path.exists(_JSON_PATH):
        return
    try:
        with open(_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return
        async with get_db() as db:
            for uid_str, queries in data.items():
                uid = int(uid_str)
                for query in reversed(queries):
                    await db.execute(
                        "INSERT INTO history (uid, query) VALUES (?, ?)",
                        (uid, query)
                    )
            await db.commit()
        os.rename(_JSON_PATH, _JSON_PATH + ".migrated")
        log.info(f"[HISTORY] Migrated from JSON")
    except Exception as e:
        log.error(f"[HISTORY] Migration error: {e}")

async def add_query(uid: int, query: str):
    async with get_db() as db:
        await db.execute("DELETE FROM history WHERE uid = ? AND query = ?", (uid, query))
        await db.execute("INSERT INTO history (uid, query) VALUES (?, ?)", (uid, query))
        await db.execute("""
            DELETE FROM history WHERE uid = ? AND id NOT IN (
                SELECT id FROM history WHERE uid = ? ORDER BY created_at DESC LIMIT ?
            )
        """, (uid, uid, _MAX))
        await db.commit()

async def get_history(uid: int) -> list:
    async with get_db() as db:
        async with db.execute(
            "SELECT query FROM history WHERE uid = ? ORDER BY created_at DESC LIMIT ?",
            (uid, _MAX)
        ) as cur:
            rows = await cur.fetchall()
            return [row["query"] for row in rows]

async def clear_history(uid: int):
    async with get_db() as db:
        await db.execute("DELETE FROM history WHERE uid = ?", (uid,))
        await db.commit()
