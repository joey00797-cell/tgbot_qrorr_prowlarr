import logging
import random
import re
import time
from datetime import timedelta
from aiogram import Router, types, F
from aiogram.types import LinkPreviewOptions

router = Router()
log = logging.getLogger("torrent_bot")
_START_TIME = time.time()

STOP_WORDS = ["админ", "админка", "администратор", "admin", "панель", "управление", "/admin", "/админ"]
PING_WORDS = ["ты тут", "на месте", "привет", "живой", "ping", "пинг", "здарова", "ку"]
UPTIME_WORDS = ["аптайм", "uptime", "сколько работаешь", "давно работаешь"]

PING_RESPONSES = [
    "На месте! Готов искать раздачи. Что качаем?",
    "На связи.",
    "Ку!",
    "Да тут я, тут, не паникуй",
    "Чего тебе??",
    "!%@VGT&64)+b",
    "На посту."
]

def _get_uptime() -> str:
    delta = timedelta(seconds=int(time.time() - _START_TIME))
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}д")
    if hours: parts.append(f"{hours}ч")
    if minutes: parts.append(f"{minutes}м")
    if not parts: parts.append(f"{seconds}с")
    return " ".join(parts)

def _has_word(text: str, words: list) -> bool:
    for word in words:
        if ' ' in word:
            if word in text: return True
        else:
            if re.search(rf'\b{re.escape(word)}\b', text): return True
    return False

def _is_bot_command(text: str):
    t = text.lower().strip()
    if not t.startswith("бот"):
        return False, None
    rest = t[3:].strip()
    if any(w in rest for w in ["рандом", "random", "посоветуй", "что посмотреть"]):
        return True, "random"
    if any(w in rest for w in ["фильм", "movie", "кино"]):
        return True, "movie"
    if any(w in rest for w in ["сериал", "serial", "сериальчик"]):
        return True, "tv"
    return False, None

@router.message(F.text)
async def handle_talking(message: types.Message, next_handler=None):
    text = message.text.lower().strip()

    if text in STOP_WORDS:
        await message.answer("Ничего не найдено.")
        return True

    if _has_word(text, UPTIME_WORDS):
        await message.answer(f"Работаю уже {_get_uptime()}")
        return True

    if _has_word(text, PING_WORDS) and not text.startswith("бот"):
        await message.answer(random.choice(PING_RESPONSES))
        return True

    is_bot_cmd, media_type = _is_bot_command(text)
    if is_bot_cmd:
        from storage.preferences import get_settings, get_liked_genre_ids, get_excluded_genre_ids
        from services.discover import discover
        from routers.recommend import build_result_keyboard, _last_result, _shown_ids

        uid = message.from_user.id
        settings = await get_settings(uid)
        mt = "tv" if media_type == "tv" else "movie"

        msg = await message.answer("Подбираю...")
        result = await discover(
            media_type=mt,
            genre_ids=await get_liked_genre_ids(uid) or None,
            excluded_genre_ids=await get_excluded_genre_ids(uid) or None,
            min_year=settings["min_year"],
            min_rating=settings["min_rating"],
            random_pick=True,
            shown_ids=_shown_ids.get(uid)
        )
        await msg.delete()

        if result and not result.get("exhausted"):
            shown = _shown_ids.get(uid, [])
            shown.append(result["tmdb_id"])
            _shown_ids[uid] = shown
            _last_result[uid] = result

            from aiogram.utils.keyboard import InlineKeyboardBuilder
            type_label = "Фильм" if mt == "movie" else "Сериал"
            title = result["title"]
            release = result["release"]
            rating = result["rating"]
            genres = result["genres"]
            overview = result["overview"]
            out = f"{type_label} <b>{title}</b> ({release})\n{rating:.1f} | {genres}\n\n<i>{overview}</i>"
            kb = build_result_keyboard(mt)
            if result.get("poster"):
                await message.answer_photo(photo=result["poster"], caption=out,
                                           reply_markup=kb, parse_mode="HTML")
            else:
                await message.answer(out, reply_markup=kb, parse_mode="HTML")
        elif result and result.get("exhausted"):
            _shown_ids.pop(uid, None)
            await message.answer("Все результаты показаны! Попробуй изменить параметры в Мои предпочтения.")
        else:
            await message.answer("Ничего не нашлось, попробуй позже.")
        return True

    return False
