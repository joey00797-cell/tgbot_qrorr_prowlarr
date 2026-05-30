import json
import os
import asyncio

_DB_PATH = "/app/app_v2/storage/downloads.json"
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
        except json.JSONDecodeError:
            return {}

def _save(data: dict):
    with open(_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

async def save_download(hash_id: str, uid: int, title: str, notify: str = "me"):
    async with _lock:
        db = _load()
        db[hash_id.lower()] = {
            "uid": uid,
            "title": title,
            "notify": notify,  # "me" или "all"
        }
        _save(db)

def get_download(hash_id: str):
    db = _load()
    return db.get(hash_id.lower())

def remove_download(hash_id: str):
    db = _load()
    db.pop(hash_id.lower(), None)
    _save(db)
