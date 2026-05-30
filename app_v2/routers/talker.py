import logging
import random
import re
import time
from datetime import timedelta
from aiogram import Router, types, F

router = Router()
log = logging.getLogger("torrent_bot")

_START_TIME = time.time()

STOP_WORDS = ["админ", "админка", "администратор", "admin", "панель", "управление", "/admin", "/админ"]
PING_WORDS = ["ты тут", "на месте", "бот", "привет", "живой", "ping", "пинг", "здарова", "ку"]
UPTIME_WORDS = ["аптайм", "uptime", "сколько работаешь", "давно работаешь"]

PING_RESPONSES = [
    "👋 На месте! Готов искать раздачи. Что качаем?",
    "⚡ На связи.",
    "🤖 Ку!",
    "🍿 Да тут я, тут, не паникуй",
    "🫡 Чего тебе??",
    "🦾 !%@VGT&64)+b",
    "🕵️‍♂️ На посту."
]

def _get_uptime() -> str:
    delta = timedelta(seconds=int(time.time() - _START_TIME))
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days}д")
    if hours:
        parts.append(f"{hours}ч")
    if minutes:
        parts.append(f"{minutes}м")
    if not parts:
        parts.append(f"{seconds}с")

    return " ".join(parts)

def _has_ping_word(text: str) -> bool:
    for word in PING_WORDS:
        if ' ' in word:
            if word in text:
                return True
        else:
            if re.search(rf'\b{re.escape(word)}\b', text):
                return True
    return False

def _has_uptime_word(text: str) -> bool:
    for word in UPTIME_WORDS:
        if word in text:
            return True
    return False

@router.message(F.text)
async def handle_talking(message: types.Message, next_handler=None):
    clean_text = message.text.lower().strip()

    if clean_text in STOP_WORDS:
        await message.answer("❌ Ничего не найдено.")
        return True

    if _has_uptime_word(clean_text):
        await message.answer(f"⏱ Работаю уже {_get_uptime()}")
        return True

    if _has_ping_word(clean_text):
        await message.answer(random.choice(PING_RESPONSES))
        return True

    return False
