import json
import os
import asyncio

_DB_PATH = "/app/app_v2/storage/history.json"
_lock = asyncio.Lock()
_MAX = 50  # максимум запросов на юзера

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

async def add_query(uid: int, query: str):
    async with _lock:
        db = _load()
        key = str(uid)
        history = db.get(key, [])
        # Убираем дубль если уже есть
        if query in history:
            history.remove(query)
        history.insert(0, query)
        db[key] = history[:_MAX]
        _save(db)

def get_history(uid: int) -> list:
    db = _load()
    return db.get(str(uid), [])

async def clear_history(uid: int):
    async with _lock:
        db = _load()
        db.pop(str(uid), None)
        _save(db)
