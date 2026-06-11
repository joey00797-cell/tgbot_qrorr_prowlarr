# -*- coding: utf-8 -*-
import logging
from storage.database import get_db

log = logging.getLogger("torrent_bot")
_cache: dict = {}

async def init_users():
    import json, os, config
    
    # Миграция из JSON
    if hasattr(config, 'USERS_DB') and os.path.exists(config.USERS_DB):
        try:
            with open(config.USERS_DB, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data:
                async with get_db() as db:
                    for uid_str, info in data.items():
                        await db.execute(
                            "INSERT OR IGNORE INTO users (user_id, username, role, status, full_name) VALUES (?, ?, ?, ?, ?)",
                            (int(uid_str), info.get("username"), info.get("role", "user"),
                             info.get("status", "pending"), info.get("full_name") or info.get("name"))
                        )
                    await db.commit()
                os.rename(config.USERS_DB, config.USERS_DB + ".migrated")
                log.info(f"[USERS] Migrated {len(data)} users from JSON")
        except Exception as e:
            log.error(f"[USERS] Migration error: {e}")
    
    # Загружаем в кэш
    try:
        async with get_db() as db:
            async with db.execute("SELECT user_id, username, role, status, full_name FROM users") as cur:
                rows = await cur.fetchall()
        
        _cache.clear()
        for row in rows:
            # row может быть tuple или sqlite3.Row
            if isinstance(row, tuple):
                uid = row[0]
                _cache[uid] = {
                    "user_id": row[0],
                    "username": row[1],
                    "role": row[2],
                    "status": row[3],
                    "full_name": row[4]
                }
            else:
                d = dict(row)
                _cache[d["user_id"]] = d
        
        log.info(f"[USERS] Loaded {len(_cache)} users into cache")
    except Exception as e:
        log.error(f"[USERS] Error loading cache: {e}")

def get_user(user_id: int) -> dict | None:
    return _cache.get(int(user_id))

async def get_user_async(user_id: int) -> dict | None:
    return _cache.get(int(user_id))

async def set_user(user_id: int, payload: dict):
    uid = int(user_id)
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, role, status, full_name) VALUES (?, ?, ?, ?, ?)",
            (uid, payload.get("username"), payload.get("role", "user"),
             payload.get("status", "pending"), payload.get("full_name") or payload.get("name"))
        )
        await db.commit()
    _cache[uid] = {"user_id": uid, **payload}

async def update_user(user_id: int, updates: dict):
    uid = int(user_id)
    allowed = {"username", "role", "status", "full_name"}
    async with get_db() as db:
        for key, val in updates.items():
            if key in allowed:
                await db.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (val, uid))
        await db.commit()
    if uid in _cache:
        _cache[uid].update(updates)
    else:
        _cache[uid] = {"user_id": uid, **updates}

def load_users() -> dict:
    import sqlite3
    result = {}
    conn = sqlite3.connect('/app/app_v2/storage/bot.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, role, status, full_name FROM users")
    rows = cur.fetchall()
    conn.close()
    
    for row in rows:
        uid = str(row[0])
        result[uid] = {
            "username": row[1] or "",
            "role": row[2] or "user",
            "status": row[3] or "pending",
            "full_name": row[4] or ""
        }
    return result

def get_all_active_users() -> list:
    return [d for d in _cache.values() if d.get("status") == "active"]
