import logging
from storage.database import get_db

log = logging.getLogger("torrent_bot")

async def init_preferences():
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                uid INTEGER PRIMARY KEY,
                min_year INTEGER DEFAULT 2000,
                min_rating REAL DEFAULT 6.5,
                use_history INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_genres (
                uid INTEGER,
                genre_id INTEGER,
                genre_name TEXT,
                status INTEGER DEFAULT 1,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (uid, genre_id)
            )
        """)
        await db.commit()

async def get_settings(uid: int) -> dict:
    async with get_db() as db:
        async with db.execute("SELECT * FROM user_settings WHERE uid = ?", (uid,)) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
            return {"uid": uid, "min_year": 2000, "min_rating": 6.5, "use_history": 1}

async def save_settings(uid: int, min_year: int = None, min_rating: float = None, use_history: int = None):
    s = await get_settings(uid)
    if min_year is not None: s["min_year"] = min_year
    if min_rating is not None: s["min_rating"] = min_rating
    if use_history is not None: s["use_history"] = use_history
    async with get_db() as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_settings (uid, min_year, min_rating, use_history)
            VALUES (?, ?, ?, ?)
        """, (uid, s["min_year"], s["min_rating"], s["use_history"]))
        await db.commit()

async def get_genres(uid: int) -> list:
    async with get_db() as db:
        async with db.execute("SELECT * FROM user_genres WHERE uid = ? ORDER BY count DESC", (uid,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def get_liked_genre_ids(uid: int) -> list:
    async with get_db() as db:
        async with db.execute(
            "SELECT genre_id FROM user_genres WHERE uid = ? AND status = 1", (uid,)
        ) as cur:
            rows = await cur.fetchall()
            return [r["genre_id"] for r in rows]

async def get_excluded_genre_ids(uid: int) -> list:
    async with get_db() as db:
        async with db.execute(
            "SELECT genre_id FROM user_genres WHERE uid = ? AND status = -1", (uid,)
        ) as cur:
            rows = await cur.fetchall()
            return [r["genre_id"] for r in rows]

async def set_genre_status(uid: int, genre_id: int, genre_name: str, status: int):
    async with get_db() as db:
        existing = await db.execute(
            "SELECT status FROM user_genres WHERE uid = ? AND genre_id = ?", (uid, genre_id)
        )
        row = await existing.fetchone()
        if row and row["status"] == status:
            await db.execute("DELETE FROM user_genres WHERE uid = ? AND genre_id = ?", (uid, genre_id))
        else:
            await db.execute("""
                INSERT OR REPLACE INTO user_genres (uid, genre_id, genre_name, status, count)
                VALUES (?, ?, ?, ?, COALESCE((SELECT count FROM user_genres WHERE uid=? AND genre_id=?), 0))
            """, (uid, genre_id, genre_name, status, uid, genre_id))
        await db.commit()

async def add_genre_from_history(uid: int, genre_id: int, genre_name: str):
    async with get_db() as db:
        existing = await db.execute(
            "SELECT status, count FROM user_genres WHERE uid = ? AND genre_id = ?", (uid, genre_id)
        )
        row = await existing.fetchone()
        if row:
            if row["status"] == -1:
                return
            await db.execute(
                "UPDATE user_genres SET count = count + 1 WHERE uid = ? AND genre_id = ?",
                (uid, genre_id)
            )
        else:
            await db.execute(
                "INSERT INTO user_genres (uid, genre_id, genre_name, status, count) VALUES (?, ?, ?, 1, 1)",
                (uid, genre_id, genre_name)
            )
        await db.commit()

async def reset_preferences(uid: int):
    async with get_db() as db:
        await db.execute("DELETE FROM user_genres WHERE uid = ?", (uid,))
        await db.execute("DELETE FROM user_settings WHERE uid = ?", (uid,))
        await db.commit()
