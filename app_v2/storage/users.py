import json
import os
import asyncio
import config

# Создаем глобальный замок для потокобезопасной работы с файлом
db_lock = asyncio.Lock()

def ensure_users_db():
    if not os.path.exists(config.USERS_DB):
        with open(config.USERS_DB, "w", encoding="utf-8") as f:
            json.dump({}, f)

def load_users():
    ensure_users_db()
    with open(config.USERS_DB, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Если файл вдруг оказался пустым или битым, возвращаем пустой словарь
            return {}

def save_users(data: dict):
    with open(config.USERS_DB, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )

def get_user(user_id: int):
    # Чтение оставляем синхронным и быстрым, так как оно не ломает структуру файла
    users = load_users()
    return users.get(str(user_id))

async def set_user(user_id: int, payload: dict):
    # Захватываем замок перед записью
    async with db_lock:
        users = load_users()
        users[str(user_id)] = payload
        save_users(users)

async def update_user(user_id: int, updates: dict):
    # Захватываем замок перед обновлением
    async with db_lock:
        users = load_users()
        uid = str(user_id)
        if uid not in users:
            users[uid] = {}
        users[uid].update(updates)
        save_users(users)
