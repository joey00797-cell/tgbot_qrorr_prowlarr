import asyncio
import html
import logging
import re
from aiogram import Router, types, F
from aiogram.types import LinkPreviewOptions, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from routers.talker import handle_talking
from services.prowlarr import search as search_prowlarr
from services.metadata import get_movie_metadata
from storage.downloads import save_download, find_similar_downloads
from storage.history import add_query
from storage.watchlist import add_watch, get_watch
import config as _config

router = Router()
log = logging.getLogger("torrent_bot")

search_results_cache = {}  # uid -> {"results": [...], "query": "..."}
pending_choices = {}        # uid -> {"hash": ..., "cat": ..., "notify": ..., "title": ...}
meta_cache = {}             # uid -> {"tmdb_title": ..., "tmdb_title_ru": ...}

MENU_BUTTONS = {
    "📊 Статус закачек",
    "📥 Добавить торрент",
    "🔍 Поиск торрентов",
    "⚙️ Админка",
    "🏠 Главное меню",
}

SESSION_EXPIRED = "⏰ Сессия поиска устарела — отправь запрос заново."

CAT_MOVIE = _config.QBIT_CAT_MOVIE
CAT_TV    = _config.QBIT_CAT_TV
CAT_NONE  = "none"

def e(text: str) -> str:
    return html.escape(str(text))

def detect_category(title: str) -> str:
    t = title.lower()
    tv_patterns = [
        r's\d{1,2}e\d{1,2}', r'\[s\d{2}\]', r'\(s\d{2}\)',
        r's\d{2}e\d', r'сезон\s*\d', r'season\s*\d', r'e\d{1,2}\s*of\s*\d',
    ]
    return CAT_TV if any(re.search(p, t) for p in tv_patterns) else CAT_MOVIE

def clean_and_format_title(raw_title: str, search_query: str = None) -> str:
    has_russian = bool(re.search('[а-яА-Я]', raw_title))
    if not has_russian and search_query:
        clean_query = search_query.strip().capitalize()
        if not raw_title.lower().startswith(clean_query.lower()):
            return f"{clean_query} / {raw_title}"
    return raw_title

def build_choice_keyboard(uid: int):
    choice = pending_choices.get(uid, {})
    cat = choice.get("cat")
    notify = choice.get("notify")
    watch = choice.get("watch", False)

    tv_label  = "📺 Сериал ✓" if cat == CAT_TV    else "📺 Сериал"
    mov_label = "🎬 Фильм ✓"  if cat == CAT_MOVIE else "🎬 Фильм"
    non_label = "📦 Прочее ✓" if cat == CAT_NONE  else "📦 Прочее"
    me_label  = "🔔 Только мне ✓" if notify == "me"  else "🔔 Только мне"
    all_label = "📢 Всем ✓"       if notify == "all" else "📢 Всем"
    watch_label = "🔄 Следить ✓" if watch else "🔄 Следить за обновлениями"

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text=tv_label,  callback_data="choice_cat_tv"),
        InlineKeyboardButton(text=mov_label, callback_data="choice_cat_movie"),
        InlineKeyboardButton(text=non_label, callback_data="choice_cat_none"),
    )
    kb.row(
        InlineKeyboardButton(text=me_label,  callback_data="choice_notify_me"),
        InlineKeyboardButton(text=all_label, callback_data="choice_notify_all"),
    )
    kb.row(InlineKeyboardButton(text=watch_label, callback_data="choice_watch"))
    if cat is not None and notify is not None:
        kb.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data="choice_confirm"))
    else:
        kb.row(InlineKeyboardButton(text="⬜ Выбери категорию и уведомление", callback_data="choice_noop"))
    kb.row(InlineKeyboardButton(text="❌ Отмена", callback_data="choice_cancel"))
    return kb.as_markup()

def local_generate_search_page(results, page=1, per_page=5, search_query=None):
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    sliced = results[start:end]
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    text = f"🔍 <b>Результаты поиска (Стр. {page} из {total_pages}):</b>\n\n"
    kb_builder = InlineKeyboardBuilder()

    for i, item in enumerate(sliced, start=start+1):
        seeds = item.get("seeders", 0)
        peers = item.get("leechers", 0)
        size_gb = round(item.get("size", 0) / (1024**3), 2) if item.get("size") else 0
        torrent_url = item.get("infoUrl") or item.get("comments") or item.get("guid") or "#"
        indexer_name = e(item.get('indexer', 'Prowlarr'))
        tracker_link = f"<a href='{torrent_url}'>{indexer_name}</a>" if torrent_url != "#" else indexer_name
        final_title = e(clean_and_format_title(item['title'], search_query))

        text += f"<b>{i}) {final_title}</b>\n"
        text += f"{size_gb} GB | ↑ {seeds} - ↓ {peers} | {tracker_link}\n\n"
        kb_builder.add(InlineKeyboardButton(text=f"{i}", callback_data=f"view_{i}_{page}"))

    kb_builder.adjust(5)
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"page_{page-1}"))
    if end < total:
        nav_buttons.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"page_{page+1}"))
    nav_builder = InlineKeyboardBuilder()
    if nav_buttons:
        nav_builder.row(*nav_buttons)
    nav_builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="search_refresh"),
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"),
    )
    kb_builder.attach(nav_builder)
    return text, kb_builder.as_markup()

def local_generate_detail_page(item, idx, page, similar=None):
    size_gb = round(item.get("size", 0) / (1024**3), 2) if item.get("size") else 0
    torrent_url = item.get("infoUrl") or item.get("comments") or item.get("guid") or "#"
    indexer_name = e(item.get('indexer', 'Prowlarr'))
    tracker_link = f"<a href='{torrent_url}'>{indexer_name}</a>" if torrent_url != "#" else indexer_name

    text = (f"📄 <b>Карточка раздачи №{idx}</b>\n\n"
            f"<b>Название:</b> {e(item['title'])}\n"
            f"<b>Размер:</b> {size_gb} GB\n"
            f"<b>Сиды:</b> {item.get('seeders', 0)} | <b>Пиры:</b> {item.get('leechers', 0)}\n"
            f"<b>Трекер:</b> {tracker_link}")

    if similar:
        matches = ", ".join(m["title"][:40] + " (" + str(m["similarity"]) + "%)" for m in similar[:2])
        text += "\n\n⚠️ <b>Похожее уже есть в базе:</b> " + matches
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📥 Скачать", callback_data=f"dl_{idx}"))
    kb.row(
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"page_{page}"),
        InlineKeyboardButton(text="📊 Статус закачек", callback_data="qbit_page_1"),
    )
    return text, kb.as_markup()


@router.message(F.text)
async def handle_search(message: types.Message):
    text = message.text.strip()
    if text in MENU_BUTTONS or text.startswith("/") or text.startswith("magnet:"):
        return
    force_search = text.startswith("!")
    query = text[1:].strip() if force_search else text
    if not query or len(query) < 2:
        return
    if not force_search:
        if await handle_talking(message):
            return

    msg = await message.answer("⏳ Ищу...")
    user = message.from_user
    username = f"@{user.username}" if user.username else "no_username"
    user_info = f"ID: {user.id} | {username} ({user.full_name})"

    try:
        import time as _time
        prefix = "[!] " if force_search else ""
        _t = _time.time()
        raw_results = await search_prowlarr(query)
        _ms = int((_time.time() - _t) * 1000)
        results = sorted(raw_results, key=lambda x: int(x.get("seeders", 0)), reverse=True)
        log.info(f"[SEARCH] {prefix}{user_info} | \"{query}\" → {len(results)} results | {_ms}ms")
        search_results_cache[message.from_user.id] = {"results": results, "query": query}
        await add_query(message.from_user.id, query)

        if not results:
            await msg.edit_text("❌ Ничего не найдено.")
            return

        await msg.delete()
        text_out, markup = local_generate_search_page(results, page=1, search_query=query)
        await message.answer(text_out, parse_mode="HTML", reply_markup=markup,
                             link_preview_options=LinkPreviewOptions(is_disabled=True))
    except asyncio.TimeoutError:
        log.warning(f"[SEARCH] Таймаут поиска для [{user_info}]: \"{query}\"")
        try:
            await msg.edit_text("⏱ Поиск занял слишком много времени — попробуй ещё раз.")
        except:
            await message.answer("⏱ Поиск занял слишком много времени — попробуй ещё раз.")
    except Exception as ex:
        log.error(f"[SEARCH] Ошибка поиска для [{user_info}]: {ex}", exc_info=True)
        try:
            await msg.edit_text(f"⚠️ Ошибка поиска:\n{str(ex)}")
        except:
            await message.answer(f"⚠️ Ошибка поиска:\n{str(ex)}")


@router.callback_query(F.data.startswith("page_"))
async def paginate(c: types.CallbackQuery):
    page = int(c.data.split("_")[1])
    cached = search_results_cache.get(c.from_user.id)
    if not cached:
        return await c.answer(SESSION_EXPIRED, show_alert=True)
    results = cached.get("results", [])
    query = cached.get("query")
    text, markup = local_generate_search_page(results, page=page, search_query=query)
    try:
        if c.message.photo:
            await c.message.delete()
            await c.message.answer(text, reply_markup=markup, parse_mode="HTML",
                                   link_preview_options=LinkPreviewOptions(is_disabled=True))
        else:
            await c.message.edit_text(text, reply_markup=markup, parse_mode="HTML",
                                      link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception:
        await c.answer()


@router.callback_query(F.data.startswith("view_"))
async def view_item(c: types.CallbackQuery):
    _, idx, page = c.data.split("_")
    cached = search_results_cache.get(c.from_user.id)
    if not cached:
        return await c.answer(SESSION_EXPIRED, show_alert=True)
    results = cached.get("results", [])
    if int(idx) > len(results):
        return await c.answer(SESSION_EXPIRED, show_alert=True)

    item = results[int(idx) - 1]
    item_year = item.get('year')
    if not item_year and item.get('publishDate'):
        item_year = item['publishDate'][:4]
    if not item_year:
        match = re.search(r'\((\d{4})\)', item['title'])
        if match:
            item_year = match.group(1)

    try:
        meta = await get_movie_metadata(item['title'], year=str(item_year) if item_year else None)
    except Exception as ex:
        log.error(f"[SEARCH] Ошибка TMDB: {ex}")
        meta = None

    similar = await find_similar_downloads(item.get("title", ""))
    text, markup = local_generate_detail_page(item, idx, page, similar=similar)
    poster_url = None

    if meta:
        meta_cache[c.from_user.id] = {
            "tmdb_title": meta.get("title", ""),
        }
        overview = e(meta.get('overview', ''))
        if len(overview) > 700:
            overview = overview[:700] + "..."
        genres = meta.get('genres')
        genre_line = f"\n🎭 <b>Жанр:</b> {e(genres)}" if genres else ""
        text += (f"\n\n🎬 <b>{e(meta.get('title', 'Без названия'))}</b> "
                 f"({e(meta.get('release', '')[:4])})"
                 f"{genre_line}\n\n"
                 f"ℹ️ <b>Описание:</b>\n<i>{overview}</i>")
        poster_url = meta.get('poster_url')

    try:
        if poster_url:
            await c.message.delete()
            await c.message.answer_photo(
                photo=poster_url,
                caption=text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await c.message.edit_text(text, reply_markup=markup, parse_mode="HTML",
                                      link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception:
        await c.answer()
        if poster_url:
            await c.message.delete()
            await c.message.answer_photo(
                photo=poster_url,
                caption=text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await c.message.edit_text(text, reply_markup=markup, parse_mode="HTML",
                                      link_preview_options=LinkPreviewOptions(is_disabled=True))


@router.callback_query(F.data.startswith("dl_"))
async def download_torrent_callback(c: types.CallbackQuery):
    parts = c.data.split("_")
    idx = int(parts[1])

    cached = search_results_cache.get(c.from_user.id)
    if not cached:
        return await c.answer(SESSION_EXPIRED, show_alert=True)
    results = cached.get("results", [])
    if idx > len(results):
        return await c.answer(SESSION_EXPIRED, show_alert=True)
    item = results[idx - 1]
    torrent_url = item.get("downloadUrl") or item.get("magnetUrl")
    title = item.get("title", "Unknown")
    indexer = item.get("indexer", "unknown")
    url_type = "magnet" if (item.get("magnetUrl") and not item.get("downloadUrl")) else "torrent"

    if not torrent_url:
        return await c.answer("❌ Ссылка на скачивание не найдена.", show_alert=True)

    log.info(f"[DL] {c.from_user.id} | {indexer} | {url_type} | {title[:40]}")

    if c.message.photo:
        await c.message.delete()
        proc_msg = await c.message.answer(
            f"⏳ <b>Получаю торрент...</b>\n\n📦 {e(title[:50])}",
            parse_mode="HTML"
        )
    else:
        proc_msg = await c.message.edit_text(
            f"⏳ <b>Получаю торрент...</b>\n\n📦 {e(title[:50])}",
            parse_mode="HTML"
        )

    try:
        from services.qbittorrent import qb
        result = await qb.add_magnet(torrent_url, paused=True)

        if result == "duplicate":
            torrents = await qb.torrents()
            found = None
            title_lower = title.lower()
            for t in torrents:
                t_name = t.get("name", "").lower()
                if t_name[:40] in title_lower or title_lower[:40] in t_name:
                    found = t
                    break
            if found:
                progress = int(found.get("progress", 0) * 100)
                eta = found.get("eta", -1)
                if eta == 8640000 or eta < 0:
                    eta_str = "∞"
                elif eta >= 3600:
                    eta_str = f"{eta // 3600}ч {(eta % 3600) // 60}м"
                elif eta >= 60:
                    eta_str = f"{eta // 60}м"
                else:
                    eta_str = f"{eta}с"
                state_map = {
                    "downloading": "⬇️ Загружается", "stalledDL": "⏸ Ожидание пиров",
                    "uploading": "⬆️ Раздаётся", "pausedDL": "⏸ На паузе",
                    "pausedUP": "✅ Завершён", "queuedDL": "🕐 В очереди",
                    "checkingDL": "🔍 Проверка", "metaDL": "🔎 Загрузка метаданных",
                }
                state_str = state_map.get(found.get("state", ""), f"❓ {found.get('state', '')}")
                await proc_msg.edit_text(
                    f"⚠️ <b>Торрент уже в списке!</b>\n\n"
                    f"📦 {e(found['name'][:45])}\n"
                    f"📊 {state_str} | 🔄 {progress}% | ⏱ {eta_str}",
                    parse_mode="HTML"
                )
            else:
                await proc_msg.edit_text("⚠️ Торрент уже добавлен в qBittorrent.", parse_mode="HTML")
            return

        if not result:
            await proc_msg.edit_text("❌ qBittorrent отклонил добавление торрента.", parse_mode="HTML")
            return

        # Получаем hash
        if isinstance(result, str) and len(result) == 40:
            hash_id = result.lower()
        else:
            hash_id = None
            for _ in range(15):
                await asyncio.sleep(1)
                try:
                    torrents = await qb.torrents()
                    title_lower = title.lower()
                    for t in torrents:
                        t_name = t.get("name", "").lower()
                        if t_name[:40] in title_lower or title_lower[:40] in t_name:
                            hash_id = t.get("hash", "").lower()
                            break
                    if hash_id:
                        break
                except Exception:
                    pass

        if not hash_id:
            await proc_msg.edit_text(
                f"✅ <b>Добавлено на паузе!</b>\n\n"
                f"📦 {e(title[:50])}\n"
                f"⚠️ Не удалось отследить хеш — категорию и запуск установите вручную.",
                parse_mode="HTML"
            )
            return

        # Сохраняем pending с автокатегорией, торрент на паузе
        auto_cat = detect_category(title)
        auto_watch = "(обновляемая)" in title.lower()
        _meta = meta_cache.get(c.from_user.id, {})
        pending_choices[c.from_user.id] = {
            "hash": hash_id,
            "cat": auto_cat,
            "notify": None,
            "title": title,
            "tmdb_title": _meta.get("tmdb_title", ""),
            "watch": auto_watch,
        }

        log.info(f"[SEARCH] {c.from_user.id} добавил на паузе: {title[:40]} | hash={hash_id[:8]}...")

        await proc_msg.edit_text(
            f"⏸ <b>Торрент на паузе.</b> Выбери параметры и подтверди запуск:\n\n"
            f"📦 {e(title[:50])}",
            reply_markup=build_choice_keyboard(c.from_user.id),
            parse_mode="HTML"
        )

    except Exception as ex:
        log.error(f"[SEARCH] Ошибка добавления торрента: {ex}", exc_info=True)
        try:
            await proc_msg.edit_text(f"❌ Ошибка: {str(ex)[:100]}", parse_mode="HTML")
        except:
            pass


@router.callback_query(F.data == "search_refresh")
async def search_refresh(c: types.CallbackQuery):
    cached = search_results_cache.get(c.from_user.id)
    if not cached:
        return await c.answer(SESSION_EXPIRED, show_alert=True)
    query = cached.get("query")
    await c.message.edit_text(f"⏳ Обновляю: <i>{query}</i>...", parse_mode="HTML")
    try:
        import time as _time
        _t = _time.time()
        raw_results = await search_prowlarr(query)
        _ms = int((_time.time() - _t) * 1000)
        results = sorted(raw_results, key=lambda x: int(x.get("seeders", 0)), reverse=True)
        search_results_cache[c.from_user.id] = {"results": results, "query": query}
        log.info(f"[SEARCH] refresh {c.from_user.id} | \"{query}\" → {len(results)} results | {_ms}ms")
        if not results:
            await c.message.edit_text("❌ Ничего не найдено.")
            return
        text, markup = local_generate_search_page(results, page=1, search_query=query)
        await c.message.edit_text(text, reply_markup=markup, parse_mode="HTML",
                                  link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as ex:
        log.error(f"[SEARCH] refresh error: {ex}")
        await c.message.edit_text(f"⚠️ Ошибка обновления: {str(ex)[:100]}", parse_mode="HTML")


@router.callback_query(F.data == "choice_back_search")
async def choice_back_search(c: types.CallbackQuery):
    cached = search_results_cache.get(c.from_user.id)
    if not cached:
        return await c.answer(SESSION_EXPIRED, show_alert=True)
    results = cached.get("results", [])
    query = cached.get("query")
    text, markup = local_generate_search_page(results, page=1, search_query=query)
    await c.message.edit_text(text, reply_markup=markup, parse_mode="HTML",
                              link_preview_options=LinkPreviewOptions(is_disabled=True))


@router.callback_query(F.data.startswith("choice_"))
async def handle_choice(c: types.CallbackQuery):
    uid = c.from_user.id
    action = c.data

    if action == "choice_noop":
        return await c.answer("Выбери категорию и уведомление", show_alert=False)

    if uid not in pending_choices and action not in ("choice_cancel",):
        return await c.answer(SESSION_EXPIRED, show_alert=True)

    if action == "choice_cancel":
        choice = pending_choices.pop(uid, {})
        hash_id = choice.get("hash")
        title = choice.get("title", "")
        if hash_id:
            try:
                from services.qbittorrent import qb
                await qb.delete_torrent(hashes=hash_id, delete_files=True)
                log.info(f"[SEARCH] {uid} отменил — торрент удалён: {title[:40]}")
            except Exception as ex:
                log.error(f"[SEARCH] Ошибка удаления при отмене: {ex}")
        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(text="🔍 Назад к поиску", callback_data="choice_back_search"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
        )
        await c.message.edit_text(
            f"❌ <b>Отменено.</b>\n\n📦 {e(title[:50])}\nТоррент удалён из qBittorrent.",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
        return

    elif action == "choice_cat_tv":
        pending_choices[uid]["cat"] = CAT_TV
    elif action == "choice_cat_movie":
        pending_choices[uid]["cat"] = CAT_MOVIE
    elif action == "choice_cat_none":
        pending_choices[uid]["cat"] = CAT_NONE
    elif action == "choice_notify_me":
        pending_choices[uid]["notify"] = "me"
    elif action == "choice_notify_all":
        pending_choices[uid]["notify"] = "all"
    elif action == "choice_watch":
        pending_choices[uid]["watch"] = not pending_choices[uid].get("watch", False)

    elif action == "choice_confirm":
        choice = pending_choices.pop(uid, {})
        hash_id = choice.get("hash")
        cat     = choice.get("cat")
        notify  = choice.get("notify")
        title   = choice.get("title", "Unknown")

        if not hash_id:
            return await c.answer(SESSION_EXPIRED, show_alert=True)

        from services.qbittorrent import qb

        # Устанавливаем категорию
        if cat and cat != CAT_NONE:
            try:
                await qb.set_category(hash_id, cat)
            except Exception as ex:
                log.error(f"[SEARCH] Ошибка установки категории: {ex}")

        # Проверяем дубли по названию
        similar = await find_similar_downloads(title)
        if similar:
            pending_choices[uid] = choice
            kb_dup = InlineKeyboardBuilder()
            kb_dup.row(
                InlineKeyboardButton(text="✅ Всё равно добавить", callback_data="choice_confirm_force"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="choice_cancel"),
            )
            matches = '\n'.join('  • ' + m['title'][:50] + ' (' + str(m['similarity']) + '%)' for m in similar[:3])
            await c.message.edit_text(
                "<b>⚠️ Похожий торрент уже есть в базе:</b>\n\n" + matches + "\n\nВсё равно запустить <b>" + e(title[:40]) + "</b>?",
                reply_markup=kb_dup.as_markup(),
                parse_mode="HTML"
            )
            return

        # Запускаем торрент
        await qb.resume_torrent(hash_id)

        # Сохраняем в downloads
        await save_download(hash_id, uid, title, notify, tmdb_title=choice.get("tmdb_title", ""))

        # Уведомляем админа о начале закачки
        if uid != int(_config.ADMIN_ID):
            from storage.users import get_user
            user_data = get_user(uid)
            uname = user_data.get("username", str(uid)) if user_data else str(uid)
            try:
                await c.bot.send_message(
                    chat_id=int(_config.ADMIN_ID),
                    text="📥 Новая закачка\n👤 @" + uname + " (id: " + str(uid) + ")\n📦 " + title[:60],
                )
            except Exception:
                pass


        # Сохраняем в watchlist если выбрано слежение
        if choice.get("watch"):
            from services.qbittorrent import qb as _qb
            torrents = await _qb.torrents()
            t = next((t for t in torrents if t.get("hash", "").lower() == hash_id.lower()), None)
            size = t.get("size", 0) if t else 0
            await add_watch(hash_id, uid, title, size)
            log.info(f"[WATCH] {uid} следит за: {title[:40]}")

        cat_label    = "📺 Сериал" if cat == CAT_TV else "🎬 Фильм" if cat == CAT_MOVIE else "📦 Прочее"
        notify_label = "🔔 Только тебе" if notify == "me" else "📢 Всем"
        watch_label  = "🔄 Слежу за обновлениями" if choice.get("watch") else ""

        log.info(f"[SEARCH] {uid} подтвердил запуск: {title[:40]} | {cat_label} | {notify_label}")

        watch_line = f"\n{watch_label}" if watch_label else ""
        await c.message.edit_text(
            f"✅ <b>Закачка запущена!</b>\n\n"
            f"📦 {e(title[:50])}\n"
            f"📂 {cat_label} | {notify_label}"
            f"{watch_line}\n\n"
            f"Уведомление придёт когда скачается.",
            parse_mode="HTML"
        )
        return

    # Обновляем клавиатуру
    try:
        await c.message.edit_reply_markup(reply_markup=build_choice_keyboard(uid))
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data == "choice_confirm_force")
async def choice_confirm_force(c: types.CallbackQuery):
    uid = c.from_user.id
    if uid not in pending_choices:
        return await c.answer("⏰ Сессия устарела", show_alert=True)
    c.data = "choice_confirm"
    await handle_choice(c)
