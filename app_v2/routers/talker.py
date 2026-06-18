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

RANDOM_WORDS = ["рандом", "random", "посоветуй", "что посмотреть", "не знаю что смотреть"]
MOVIE_WORDS = ["фильм", "movie", "кино"]
SERIAL_WORDS = ["сериал", "serial", "сериальчик"]

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

def _is_bot_command(text: str) -> tuple:
    """Возвращает (True, media_type) если это команда боту"""
    t = text.lower().strip()
    if not t.startswith("бот"):
        return False, None
    rest = t[3:].strip()
    if any(w in rest for w in RANDOM_WORDS):
        return True, "random"
    if any(w in rest for w in MOVIE_WORDS):
        return True, "movie"
    if any(w in rest for w in SERIAL_WORDS):
        return True, "tv"
    return False, None

@router.message(F.text)
async def handle_talking(message: types.Message, next_handler=None):
    clean_text = message.text.lower().strip()

    is_bot_cmd, media_type = _is_bot_command(clean_text)
    if is_bot_cmd:
        from storage.preferences import get_settings, get_liked_genre_ids, get_excluded_genre_ids
        from services.discover import discover
        from routers.recommend import _show_result
        uid = message.from_user.id
        settings = await get_settings(uid)
        msg = await message.answer("🎲 Подбираю...")
        mt = "movie" if media_type != "tv" else "tv"
        result = await discover(
            media_type=mt,
            genre_ids=await get_liked_genre_ids(uid) or None,
            excluded_genre_ids=await get_excluded_genre_ids(uid) or None,
            min_year=settings["min_year"],
            min_rating=settings["min_rating"],
            random_pick=True
        )
        await msg.delete()
        if result:
            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from routers.recommend import build_result_keyboard, _last_result
            _last_result[uid] = result
            type_label = "🎬 Фильм" if mt == "movie" else "📺 Сериал"
            type_label = "🎬 Фильм" if mt == "movie" else "📺 Сериал"
            title = result["title"]
            release = result["release"]
            rating = result["rating"]
            genres = result["genres"]
            overview = result["overview"]
            text = f"{type_label} <b>{title}</b> ({release})\n⭐ {rating:.1f} | 🎭 {genres}\n\n<i>{overview}</i>"
            kb = build_result_keyboard(mt)
            if result.get("poster"):
                await message.answer_photo(photo=result["poster"], caption=text,
                                           reply_markup=kb, parse_mode="HTML")
            else:
                await message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer("😔 Ничего не нашлось, попробуй позже.")
        return True

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
