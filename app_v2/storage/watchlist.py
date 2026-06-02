import json
import os
import asyncio

_DB_PATH = "/app/app_v2/storage/watchlist.json"
_lock = asyncio.Lock()

def _ensure():
    if not os.path.exists(_DB_PATH):
        with open(_DB_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)

def _load():
    _ensure()
    with open(_DB_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def _save(data: dict):
    with open(_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

async def add_watch(hash_id: str, uid: int, title: str, size: int = 0):
    async with _lock:
        db = _load()
        db[hash_id.lower()] = {
            "uid": uid,
            "title": title,
            "size": size,
        }
        _save(db)

async def remove_watch(hash_id: str):
    async with _lock:
        db = _load()
        db.pop(hash_id.lower(), None)
        _save(db)

async def update_size(hash_id: str, size: int):
    async with _lock:
        db = _load()
        if hash_id.lower() in db:
            db[hash_id.lower()]["size"] = size
            _save(db)

def get_watch(hash_id: str):
    db = _load()
    return db.get(hash_id.lower())

def get_all_watches() -> dict:
    return _load()
