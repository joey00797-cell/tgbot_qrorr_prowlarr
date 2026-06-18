import html
import logging
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, LinkPreviewOptions
from services.discover import discover, get_genres, GENRES_MOVIE, GENRES_TV
from storage.preferences import get_settings, save_settings, get_liked_genre_ids, get_excluded_genre_ids, set_genre_status, reset_preferences, get_genres

router = Router()
log = logging.getLogger("torrent_bot")

def e(text): return html.escape(str(text))

MENU_BUTTON = "🎬 Подобрать фильм"

def build_recommend_menu():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎲 Рандом", callback_data="rec_random"))
    kb.row(InlineKeyboardButton(text="🎯 Подобрать", callback_data="rec_pick"))
    kb.row(InlineKeyboardButton(text="⚙️ Мои предпочтения", callback_data="rec_prefs"))
    kb.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return kb.as_markup()

def build_genre_keyboard(media_type: str, selected: list = None):
    selected = selected or []
    genres = GENRES_MOVIE if media_type == "movie" else GENRES_TV
    kb = InlineKeyboardBuilder()
    for gid, name in genres.items():
        mark = "✓ " if gid in selected else ""
        kb.add(InlineKeyboardButton(text=f"{mark}{name}", callback_data=f"rec_genre_{media_type}_{gid}"))
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="✅ Найти!", callback_data=f"rec_find_{media_type}"))
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="rec_pick"))
    return kb.as_markup()

def build_result_keyboard(media_type: str):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔍 Найти на трекере", callback_data=f"rec_search_{media_type}"))
    kb.row(
        InlineKeyboardButton(text="🎲 Ещё", callback_data=f"rec_more_{media_type}"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="rec_pick"),
    )
    kb.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return kb.as_markup()

# временное хранилище выбранных жанров
_session_genres: dict = {}
_last_result: dict = {}  # uid -> result
_session_search: dict = {}  # uid -> {genre_ids, media_type}
_shown_ids: dict = {}  # uid -> [tmdb_id, ...]

@router.message(F.text == MENU_BUTTON)
async def recommend_menu(message: types.Message):
    await message.answer(
        "🎬 <b>Подобрать фильм или сериал</b>\n\nВыбери режим:",
        reply_markup=build_recommend_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "rec_random")
async def rec_random(c: types.CallbackQuery):
    uid = c.from_user.id
    prefs = await get_settings(uid)
    try:
        await c.message.edit_text("🎲 <b>Ищу что-нибудь интересное...</b>", parse_mode="HTML")
    except Exception:
        await c.message.delete()
        await c.message.answer("🎲 <b>Ищу что-нибудь интересное...</b>", parse_mode="HTML")
    result = await discover(
        media_type="movie",
        genre_ids=_session_search.get(uid, {}).get("genre_ids") or await get_liked_genre_ids(uid) or None,
        excluded_genre_ids=await get_excluded_genre_ids(uid) or None,
        min_year=prefs["min_year"],
        min_rating=prefs["min_rating"],
        random_pick=True,
        shown_ids=_shown_ids.get(uid)
    )
    await _show_result(c, result)

@router.callback_query(F.data == "rec_pick")
async def rec_pick(c: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🎬 Фильм", callback_data="rec_type_movie"),
        InlineKeyboardButton(text="📺 Сериал", callback_data="rec_type_tv"),
    )
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="rec_back"))
    await c.message.edit_text(
        "🎯 <b>Что ищем?</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.in_({"rec_type_movie", "rec_type_tv"}))
async def rec_type(c: types.CallbackQuery):
    media_type = "movie" if c.data == "rec_type_movie" else "tv"
    _session_genres[c.from_user.id] = []
    await c.message.edit_text(
        "🎭 <b>Выбери жанры</b> (можно несколько):",
        reply_markup=build_genre_keyboard(media_type),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("rec_genre_"))
async def rec_genre(c: types.CallbackQuery):
    _, _, media_type, gid_str = c.data.split("_", 3)
    gid = int(gid_str)
    uid = c.from_user.id
    selected = _session_genres.get(uid, [])
    if gid in selected:
        selected.remove(gid)
    else:
        selected.append(gid)
    _session_genres[uid] = selected
    await c.message.edit_reply_markup(reply_markup=build_genre_keyboard(media_type, selected))
    await c.answer()

@router.callback_query(F.data.startswith("rec_find_"))
async def rec_find(c: types.CallbackQuery):
    media_type = c.data.split("_")[2]
    uid = c.from_user.id
    selected = _session_genres.get(uid, [])
    prefs = await get_settings(uid)
    try:
        await c.message.edit_text("⏳ <b>Подбираю...</b>", parse_mode="HTML")
    except Exception:
        await c.message.delete()
        await c.message.answer("⏳ <b>Подбираю...</b>", parse_mode="HTML")
    excluded = await get_excluded_genre_ids(uid)
    _shown_ids.pop(uid, None)
    result = await discover(
        media_type=media_type,
        genre_ids=selected or None,
        excluded_genre_ids=excluded or None,
        min_year=prefs["min_year"],
        min_rating=prefs["min_rating"],
        random_pick=True,
        shown_ids=None
    )
    _session_search[uid] = {"genre_ids": selected, "media_type": media_type}
    await _show_result(c, result, media_type)

@router.callback_query(F.data.startswith("rec_more_"))
async def rec_more(c: types.CallbackQuery):
    uid = c.from_user.id
    media_type = c.data.split("_")[2]
    prefs = await get_settings(uid)
    try:
        await c.message.edit_text("🎲 <b>Ищу ещё...</b>", parse_mode="HTML")
    except Exception:
        await c.message.delete()
        await c.message.answer("🎲 <b>Ищу ещё...</b>", parse_mode="HTML")
    result = await discover(
        media_type=media_type,
        genre_ids=_session_search.get(uid, {}).get("genre_ids") or await get_liked_genre_ids(uid) or None,
        excluded_genre_ids=await get_excluded_genre_ids(uid) or None,
        min_year=prefs["min_year"],
        min_rating=prefs["min_rating"],
        random_pick=True,
        shown_ids=_shown_ids.get(uid)
    )
    await _show_result(c, result, media_type)

@router.callback_query(F.data.startswith("rec_search_"))
async def rec_search(c: types.CallbackQuery):
    parts = c.data.split("_")
    media_type = parts[2] if len(parts) > 2 else "movie"
    result = _last_result.get(c.from_user.id, {})
    title = result.get("search_query") or result.get("original_title") or result.get("title", "")
    await c.answer(show_alert=False)
    from routers.search import do_search
    try:
        msg = await c.message.edit_text(f"🔍 Ищу <b>{e(title)}</b> на трекерах...", parse_mode="HTML")
    except Exception:
        await c.message.delete()
        msg = await c.message.answer(f"🔍 Ищу <b>{e(title)}</b> на трекерах...", parse_mode="HTML")
    await do_search(c.from_user.id, title, msg, edit=True)

@router.callback_query(F.data == "rec_prefs")
async def rec_prefs(c: types.CallbackQuery):
    uid = c.from_user.id
    settings = await get_settings(uid)
    genres = await get_genres(uid)
    liked = [g for g in genres if g["status"] == 1]
    excluded = [g for g in genres if g["status"] == -1]
    use_history = settings.get("use_history", 1)

    liked_text = ", ".join(g["genre_name"] for g in liked) or "не выбраны"
    excl_text = ", ".join(g["genre_name"] for g in excluded) or "нет"
    history_label = "Вкл ✅" if use_history else "Выкл ❌"

    text = (f"⚙️ <b>Мои предпочтения</b>\n\n"
            f"❤️ <b>Нравится:</b> {liked_text}\n"
            f"🚫 <b>Не показывать:</b> {excl_text}\n"
            f"📅 <b>Год от:</b> {settings['min_year']}\n"
            f"⭐ <b>Рейтинг от:</b> {settings['min_rating']}\n"
            f"🔄 <b>Учитывать историю:</b> {history_label}")

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎭 Настроить жанры", callback_data="rec_edit_genres"))
    kb.row(
        InlineKeyboardButton(text="📅 Год", callback_data="rec_edit_year"),
        InlineKeyboardButton(text="⭐ Рейтинг", callback_data="rec_edit_rating"),
        InlineKeyboardButton(text="🔄 История", callback_data="rec_toggle_history"),
    )
    kb.row(
        InlineKeyboardButton(text="🗑 Сбросить", callback_data="rec_prefs_reset"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="rec_back"),
    )
    try:
        await c.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await c.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "rec_edit_genres")
async def rec_edit_genres(c: types.CallbackQuery):
    uid = c.from_user.id
    genres = await get_genres(uid)
    genre_status = {g["genre_id"]: g["status"] for g in genres}

    from services.discover import GENRES_MOVIE
    all_genres = GENRES_MOVIE

    kb = InlineKeyboardBuilder()
    for gid, name in all_genres.items():
        status = genre_status.get(gid, 0)
        if status == 1:
            mark = "✅ "
        elif status == -1:
            mark = "❌ "
        else:
            mark = "⬜ "
        kb.add(InlineKeyboardButton(text=f"{mark}{name}", callback_data=f"rec_toggle_genre_{gid}"))
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="rec_prefs"))
    try:
        await c.message.edit_text(
            "🎭 <b>Настройка жанров</b>\n\n"
            "✅ нравится — приоритет в поиске\n"
            "❌ не показывать — исключить\n"
            "⬜ нейтрально\n\n"
            "Нажми жанр чтобы переключить:",
            reply_markup=kb.as_markup(), parse_mode="HTML"
        )
    except Exception:
        await c.answer()

@router.callback_query(F.data.startswith("rec_toggle_genre_"))
async def rec_toggle_genre(c: types.CallbackQuery):
    uid = c.from_user.id
    gid = int(c.data.split("_")[3])

    from services.discover import GENRES_MOVIE
    genre_name = GENRES_MOVIE.get(gid, str(gid))

    genres = await get_genres(uid)
    current = next((g["status"] for g in genres if g["genre_id"] == gid), 0)

    # цикл: 0 -> 1 -> -1 -> 0
    if current == 0:
        new_status = 1
    elif current == 1:
        new_status = -1
    else:
        new_status = 0

    if new_status == 0:
        async with __import__('storage.database', fromlist=['get_db']).get_db() as db:
            await db.execute("DELETE FROM user_genres WHERE uid = ? AND genre_id = ?", (uid, gid))
            await db.commit()
    else:
        await set_genre_status(uid, gid, genre_name, new_status)

    await rec_edit_genres(c)
    await c.answer()


@router.callback_query(F.data == "rec_edit_year")
async def rec_edit_year(c: types.CallbackQuery):
    settings = await get_settings(c.from_user.id)
    cur = settings["min_year"]
    years = [1970, 1980, 1990, 2000, 2005, 2010, 2015, 2020]
    kb = InlineKeyboardBuilder()
    for y in years:
        mark = "✅ " if cur == y else ""
        kb.add(InlineKeyboardButton(text=f"{mark}{y}+", callback_data=f"rec_set_year_{y}"))
    kb.adjust(4)
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="rec_prefs"))
    await c.message.edit_text("📅 <b>Год от:</b> выбери минимальный год выхода",
                              reply_markup=kb.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("rec_set_year_"))
async def rec_set_year(c: types.CallbackQuery):
    year = int(c.data.split("_")[3])
    await save_settings(c.from_user.id, min_year=year)
    await c.answer(f"Год от {year} сохранён")
    await rec_prefs(c)

@router.callback_query(F.data == "rec_edit_rating")
async def rec_edit_rating(c: types.CallbackQuery):
    settings = await get_settings(c.from_user.id)
    cur = settings["min_rating"]
    ratings = [0, 5.0, 6.0, 6.5, 7.0, 7.5, 8.0]
    labels = ["Любой", "5+", "6+", "6.5+", "7+", "7.5+", "8+"]
    kb = InlineKeyboardBuilder()
    for r, label in zip(ratings, labels):
        mark = "✅ " if cur == r else ""
        kb.add(InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"rec_set_rating_{r}"))
    kb.adjust(4)
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="rec_prefs"))
    await c.message.edit_text("⭐ <b>Рейтинг от:</b> выбери минимальный рейтинг",
                              reply_markup=kb.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("rec_set_rating_"))
async def rec_set_rating(c: types.CallbackQuery):
    rating = float(c.data.split("_")[3])
    await save_settings(c.from_user.id, min_rating=rating)
    await c.answer(f"Рейтинг от {rating} сохранён")
    await rec_prefs(c)

@router.callback_query(F.data == "rec_toggle_history")
async def rec_toggle_history(c: types.CallbackQuery):
    settings = await get_settings(c.from_user.id)
    new_val = 0 if settings.get("use_history", 1) else 1
    await save_settings(c.from_user.id, use_history=new_val)
    await rec_prefs(c)

@router.callback_query(F.data == "rec_prefs_reset")
async def rec_prefs_reset(c: types.CallbackQuery):
    await reset_preferences(c.from_user.id)
    await c.answer("Предпочтения сброшены", show_alert=False)
    await rec_prefs(c)

@router.callback_query(F.data == "rec_back")
async def rec_back(c: types.CallbackQuery):
    await c.message.edit_text(
        "🎬 <b>Подобрать фильм или сериал</b>\n\nВыбери режим:",
        reply_markup=build_recommend_menu(),
        parse_mode="HTML"
    )
async def _show_result(c: types.CallbackQuery, result: dict, media_type: str = "movie"):
    uid = c.from_user.id
    kb_back = InlineKeyboardBuilder()
    kb_back.row(InlineKeyboardButton(text="⚙️ Изменить параметры", callback_data="rec_prefs"))
    kb_back.row(InlineKeyboardButton(text="🔙 Назад", callback_data="rec_back"))

    if not result or result.get("exhausted"):
        _shown_ids.pop(uid, None)
        if result and result.get("exhausted"):
            msg = "🏁 <b>Все результаты показаны!</b>\n\nПопробуй изменить жанр, год или рейтинг."
        else:
            msg = "😔 <b>Ничего не нашлось</b>\n\nПопробуй изменить фильтры."
        try:
            await c.message.edit_text(msg, reply_markup=kb_back.as_markup(), parse_mode="HTML")
        except Exception:
            await c.message.answer(msg, reply_markup=kb_back.as_markup(), parse_mode="HTML")
        return

    # сохраняем показанный id
    shown = _shown_ids.get(uid, [])
    shown.append(result["tmdb_id"])
    _shown_ids[uid] = shown

    type_label = "🎬 Фильм" if media_type == "movie" else "📺 Сериал"
    title = e(result["title"])
    release = result["release"]
    rating = result["rating"]
    genres = e(result["genres"])
    overview = e(result["overview"])
    text = f"{type_label} <b>{title}</b> ({release})\n⭐ {rating:.1f} | 🎭 {genres}\n\n<i>{overview}</i>"

    _last_result[uid] = result
    kb = build_result_keyboard(media_type)
    try:
        await c.message.delete()
    except Exception:
        pass
    try:
        if result.get("poster"):
            await c.message.answer_photo(
                photo=result["poster"],
                caption=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            await c.message.answer(text, reply_markup=kb, parse_mode="HTML",
                                   link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as ex:
        log.error(f"[RECOMMEND] show error: {ex}")
        await c.answer("Ошибка отображения", show_alert=True)
