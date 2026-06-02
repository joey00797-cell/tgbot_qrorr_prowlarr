import logging
import datetime
from aiogram import Router, types, F, Bot
from aiogram.types import ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.qbittorrent import qb

router = Router()
log = logging.getLogger("torrent_bot")

def _u(user) -> str:
    un = f"@{user.username}" if user.username else "no_username"
    return f"{user.id} {un}"

# =========================================================
# УТИЛИТЫ ФОРМАТИРОВАНИЯ
# =========================================================

def make_progress_bar(progress):
    length = 8
    filled = int(round(length * progress))
    return "■" * filled + "▨" * (length - filled)

def format_eta(seconds):
    if seconds > 86400 * 7 or seconds < 0:
        return "∞"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0: return f"{h}ч{m}м"
    if m > 0: return f"{m}м{s}с"
    return f"{s}с"

def get_readable_state(state, progress):
    if state in ['downloading', 'metaDL']: return "📥 Скачивается"
    if state in ['pausedDL', 'stoppedDL']: return "⏸ Пауза" if progress < 1.0 else "✅ Готов"
    if state == 'stalledDL': return "⏳ Ожидает сидов"
    if state == 'checkingDL': return "🔍 Проверка файлов"
    if state == 'uploading': return "📤 Раздается"
    if state in ['stalledUP', 'pausedUP', 'queuedUP']: return "✅ Раздача"
    if state == 'checkingUP': return "🔍 Проверка раздачи"
    return f"⚙️ {state}"

def sort_torrents(torrents):
    def get_priority(t):
        state = t.get("state", "")
        progress = t.get("progress", 0)
        if state in ['downloading', 'metaDL']: return 0
        elif state in ['stalledDL', 'pausedDL', 'stoppedDL', 'checkingDL', 'checkingUP'] and progress < 1.0: return 1
        elif state in ['uploading', 'stalledUP', 'queuedUP']: return 2
        return 3
    # Внутри каждой группы — свежедобавленные первые
    return sorted(torrents, key=lambda t: (get_priority(t), -t.get("added_on", 0)))

def format_status_page(torrents_list, global_info, page=1, per_page=10):
    if not torrents_list:
        return "📥 <b>В qBittorrent сейчас нет торрентов.</b>", False, 0

    sorted_torrents = sort_torrents(torrents_list)
    total_count = len(sorted_torrents)
    start = (page - 1) * per_page
    end = start + per_page
    page_torrents = sorted_torrents[start:end]

    dl_total = round(global_info.get("dl_info_speed", 0) / 1024 / 1024, 2)
    up_total = round(global_info.get("up_info_speed", 0) / 1024 / 1024, 2)

    msg = f"📊 <b>Мониторинг qBittorrent (Стр. {page})</b>\n"
    msg += f"📥 {dl_total} МБ/с | 📤 {up_total} МБ/с | Всего: <code>{total_count}</code>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, t in enumerate(page_torrents, start=start + 1):
        progress = t.get("progress", 0)
        progress_pct = round(progress * 100, 1)
        p_bar = make_progress_bar(progress)
        dl_speed = round(t.get("dlspeed", 0) / 1024 / 1024, 2)
        size_gb = round(t.get("size", 0) / 1024 / 1024 / 1024, 2)
        state = t.get("state", "")
        status_text = get_readable_state(state, progress)
        name = t.get("name", "unknown")

        msg += f"<b>{i})</b> <b>{name[:38]}...</b>\n"
        msg += f" └ <code>[{p_bar}]</code> <b>{progress_pct}%</b> | <code>{size_gb} ГБ</code>\n"
        msg += f" └ {status_text}"

        if t.get("dlspeed", 0) > 0 and state in ['downloading', 'metaDL']:
            msg += f" | ⬇️ {dl_speed} МБ/с | ⏱ {format_eta(t.get('eta', -1))}"

        msg += "\n────────────────────────\n"

    return msg, True, total_count

def build_status_keyboard(torrents_list, page=1, per_page=10):
    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="⏸ Пауза всех", callback_data="qbit_global_pause"),
        types.InlineKeyboardButton(text="▶️ Старт всех", callback_data="qbit_global_resume")
    )

    if torrents_list:
        sorted_torrents = sort_torrents(torrents_list)
        start = (page - 1) * per_page
        end = start + per_page
        page_torrents = sorted_torrents[start:end]
        total_count = len(sorted_torrents)

        num_builder = InlineKeyboardBuilder()
        for i, t in enumerate(page_torrents, start=start + 1):
            num_builder.add(types.InlineKeyboardButton(
                text=str(i), callback_data=f"qbit_manage_{t.get('hash', '')}"
            ))
        num_builder.adjust(5)
        kb.attach(num_builder)

        nav = []
        if page > 1:
            nav.append(types.InlineKeyboardButton(text="⏪ Назад", callback_data=f"qbit_page_{page-1}"))
        if end < total_count:
            nav.append(types.InlineKeyboardButton(text="Вперед ⏩", callback_data=f"qbit_page_{page+1}"))
        if nav:
            kb.row(*nav)

    kb.row(
        types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"qbit_page_{page}"),
        types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    return kb.as_markup()


# =========================================================
# ДАШБОРД
# =========================================================

async def send_status_dashboard(target, page=1, is_callback=False):
    try:
        torrents_list = await qb.torrents()
        global_info = await qb.global_info()
    except Exception as e:
        log.error(f"[QBIT] Dashboard error: {e}")
        msg_text = "❌ <b>Ошибка qBittorrent:</b> Не удалось получить список закачек."
        if is_callback:
            await target.message.edit_text(msg_text, parse_mode="HTML")
        else:
            await target.answer(msg_text, parse_mode="HTML")
        return

    text, has_torrents, total_count = format_status_page(torrents_list, global_info, page=page)
    markup = build_status_keyboard(torrents_list if has_torrents else None, page=page)

    if is_callback:
        try:
            await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await target.answer()
    else:
        await target.answer(text, reply_markup=markup, parse_mode="HTML")


# =========================================================
# ХЭНДЛЕРЫ
# =========================================================

@router.message(Command("status"))
@router.message(F.text == "📊 Статус закачек")
async def cmd_status(message: types.Message):
    log.info(f"[BTN] {_u(message.from_user)} | 📊 Статус закачек")
    tmp = await message.answer("🔄 Загружаю...", reply_markup=ReplyKeyboardRemove())
    await tmp.delete()
    await send_status_dashboard(message, page=1, is_callback=False)

@router.message(F.text == "📥 Добавить торрент")
async def cmd_add_torrent_hint(message: types.Message):
    log.info(f"[BTN] {_u(message.from_user)} | 📥 Добавить торрент")
    await message.answer(
        "📥 <b>Добавление торрента</b>\n\n"
        "Отправьте мне одно из следующего:\n"
        "• <b>Magnet-ссылку</b> (magnet:?xt=...)\n"
        "• <b>.torrent файл</b> — просто прикрепите файл\n"
        "• <b>Поиск</b> — напишите название и выберите из результатов",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

@router.message(F.text == "🔍 Поиск торрентов")
async def cmd_search_hint(message: types.Message):
    log.info(f"[BTN] {_u(message.from_user)} | 🔍 Поиск торрентов")
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🕐 История поиска", callback_data="show_history"))
    await message.answer(
        "🔍 <b>Поиск торрентов</b>\n\n"
        "Напиши название фильма, сериала или любого контента.\n\n"
        "💡 Можно уточнить запрос:\n"
        "• <code>Пацаны сезон 3</code> — конкретный сезон\n"
        "• <code>Пацаны лостфильм</code> — конкретная озвучка\n"
        "• <code>!бот</code> — принудительный поиск (обход болталки)",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("qbit_page_"))
async def qbit_page_callback(c: types.CallbackQuery):
    page = int(c.data.split("_")[2])
    await send_status_dashboard(c, page=page, is_callback=True)

@router.callback_query(F.data == "qbit_global_pause")
async def qbit_global_pause(c: types.CallbackQuery):
    try:
        await qb.pause_all()
        await c.answer("⏸ Все закачки приостановлены", show_alert=True)
        await send_status_dashboard(c, page=1, is_callback=True)
    except Exception as e:
        await c.answer(f"Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "qbit_global_resume")
async def qbit_global_resume(c: types.CallbackQuery):
    try:
        await qb.resume_all()
        await c.answer("▶️ Все закачки запущены", show_alert=True)
        await send_status_dashboard(c, page=1, is_callback=True)
    except Exception as e:
        await c.answer(f"Ошибка: {e}", show_alert=True)

@router.callback_query(F.data.startswith("qbit_manage_"))
async def qbit_manage_torrent(c: types.CallbackQuery, t_hash: str = None):
    if t_hash is None:
        t_hash = c.data.split("_")[2]
    try:
        from storage.downloads import get_download, save_download
        from storage.watchlist import get_watch, add_watch, remove_watch
        torrents = await qb.torrents()
        target_t = next((t for t in torrents if t.get("hash") == t_hash), None)
        if not target_t:
            return await c.answer("⚠️ Торрент не найден.", show_alert=True)
        name = target_t.get("name")
        progress = int(target_t.get("progress", 0) * 100)
        subscribed = get_download(t_hash.lower()) is not None
        watching = get_watch(t_hash.lower()) is not None

        kb = InlineKeyboardBuilder()
        kb.row(
            types.InlineKeyboardButton(text="⏸ Пауза", callback_data=f"qbit_op_pause_{t_hash}"),
            types.InlineKeyboardButton(text="▶️ Запуск", callback_data=f"qbit_op_resume_{t_hash}")
        )
        if progress < 100:
            if subscribed:
                kb.row(
                    types.InlineKeyboardButton(text="🔔 Подписан ✓", callback_data="qbit_noop"),
                    types.InlineKeyboardButton(text="🔕 Отписаться", callback_data=f"qbit_op_unsub_{t_hash}"),
                )
            else:
                kb.row(types.InlineKeyboardButton(text="🔔 Подписаться на уведомление", callback_data=f"qbit_op_sub_{t_hash}"))
        if watching:
            kb.row(
                types.InlineKeyboardButton(text="🔄 Слежу ✓", callback_data="qbit_noop"),
                types.InlineKeyboardButton(text="⏹ Не следить", callback_data=f"qbit_op_unwatch_{t_hash}"),
            )
        else:
            kb.row(types.InlineKeyboardButton(text="🔄 Следить за обновлениями", callback_data=f"qbit_op_watch_{t_hash}"))
        kb.row(types.InlineKeyboardButton(text="❌ Удалить торрент", callback_data=f"qbit_op_delete_{t_hash}"))
        kb.row(types.InlineKeyboardButton(text="🔙 Назад к списку", callback_data="qbit_page_1"))
        await c.message.edit_text(
            f"⚙️ <b>Управление:</b>\n<code>{name}</code>",
            reply_markup=kb.as_markup(), parse_mode="HTML"
        )
    except Exception as e:
        await c.answer(f"Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "qbit_noop")
async def qbit_noop(c: types.CallbackQuery):
    await c.answer()


@router.callback_query(F.data.startswith("qbit_op_"))
async def qbit_execute_op(c: types.CallbackQuery):
    parts = c.data.split("_")
    op = parts[2]
    t_hash = parts[3]
    try:
        if op == "pause":
            await qb.pause_torrent(hashes=t_hash)
            await c.answer("Приостановлено")
        elif op == "resume":
            await qb.resume_torrent(hashes=t_hash)
            await c.answer("Запущено")
        elif op == "delete":
            await qb.delete_torrent(hashes=t_hash, delete_files=True)
            await c.answer("Торрент удален с диска", show_alert=True)
            return await send_status_dashboard(c, page=1, is_callback=True)
        elif op == "sub":
            from storage.downloads import save_download
            torrents = await qb.torrents()
            target_t = next((t for t in torrents if t.get("hash") == t_hash), None)
            title = target_t.get("name", "Unknown") if target_t else "Unknown"
            await save_download(t_hash.lower(), c.from_user.id, title, "me")
            await c.answer("🔔 Подписан на уведомление")
            return await qbit_manage_torrent(c, t_hash)
        elif op == "unsub":
            from storage.downloads import remove_download
            remove_download(t_hash.lower())
            await c.answer("🔕 Отписался от уведомления")
            return await qbit_manage_torrent(c, t_hash)
        elif op == "watch":
            from storage.watchlist import add_watch
            torrents = await qb.torrents()
            target_t = next((t for t in torrents if t.get("hash") == t_hash), None)
            title = target_t.get("name", "Unknown") if target_t else "Unknown"
            size = target_t.get("size", 0) if target_t else 0
            await add_watch(t_hash.lower(), c.from_user.id, title, size)
            await c.answer("🔄 Слежу за обновлениями")
            return await qbit_manage_torrent(c, t_hash)
        elif op == "unwatch":
            from storage.watchlist import remove_watch
            await remove_watch(t_hash.lower())
            await c.answer("⏹ Слежение отключено")
            return await qbit_manage_torrent(c, t_hash)
        await qbit_manage_torrent(c, t_hash)
    except Exception as e:
        await c.answer("Ошибка операции", show_alert=True)


# =========================================================
# ПРИЕМ ССЫЛОК И ФАЙЛОВ
# =========================================================

@router.callback_query(F.data.startswith("watch_"))
@router.callback_query(F.data.startswith("watch_"))
async def handle_watch_action(c: types.CallbackQuery):
    parts = c.data.split("_")
    action = parts[1]
    hash_id = parts[2]

    if action == "stop":
        from storage.watchlist import remove_watch
        await remove_watch(hash_id)
        try:
            await c.message.edit_text(
                c.message.text + "\n\n\u23f9 <i>Слежение отключено.</i>",
                parse_mode="HTML"
            )
        except Exception:
            await c.answer("\u23f9 Слежение отключено")
        return

    if action == "update":
        from storage.watchlist import get_watch, remove_watch
        from services.prowlarr import search as search_prowlarr
        info = get_watch(hash_id)
        if not info:
            return await c.answer("Данные устарели.", show_alert=True)

        title = info.get("title", "")
        clean_title = title.split("(")[0].replace("(обновляемая)", "").strip()

        await c.message.edit_text(
            f"\u23f3 <b>Ищу обновление...</b>\n\n\U0001f4e6 {title[:50]}",
            parse_mode="HTML"
        )

        try:
            results = await search_prowlarr(clean_title)
            if not results:
                await c.message.edit_text("\u274c Раздача не найдена в Prowlarr.", parse_mode="HTML")
                return

            best = max(results, key=lambda x: x.get("size", 0))
            await qb.delete_torrent(hashes=hash_id, delete_files=False)
            await remove_watch(hash_id)

            torrent_url = best.get("downloadUrl") or best.get("magnetUrl")
            await qb.add_magnet(torrent_url, paused=True)

            new_title = best.get("title", title)
            size_gb = round(best.get("size", 0) / (1024**3), 2)

            await c.message.edit_text(
                f"\u2705 <b>Раздача обновлена!</b>\n\n"
                f"\U0001f4e6 {new_title[:50]}\n"
                f"\U0001f4be {size_gb} GB\n\n"
                f"Торрент добавлен на паузу — запусти вручную в дашборде.",
                parse_mode="HTML"
            )
            log.info(f"[WATCH] {c.from_user.id} обновил раздачу: {title[:40]}")
        except Exception as ex:
            log.error(f"[WATCH] Ошибка обновления: {ex}")
            await c.message.edit_text(f"\u274c Ошибка обновления: {str(ex)[:100]}", parse_mode="HTML")


@router.message(F.text.startswith("magnet:?"))
async def add_magnet_torrent(message: types.Message):
    user = message.from_user
    log.info(f"[MAGNET] {_u(user)} | {message.text[:60]}")
    try:
        result = await qb.add_magnet(message.text)
        if result == "duplicate":
            await message.reply("⚠️ <b>Этот торрент уже есть в qBittorrent.</b>", parse_mode="HTML")
        elif result:
            await message.reply("✅ <b>Magnet-ссылка добавлена!</b>\nСтатус: /status", parse_mode="HTML")
        else:
            await message.reply("❌ <b>qBittorrent отклонил ссылку.</b>", parse_mode="HTML")
    except Exception as e:
        log.error(f"[QBIT] Magnet add error: {e}")
        await message.reply("❌ <b>Ошибка связи с qBittorrent.</b>", parse_mode="HTML")

@router.message(F.document & F.document.file_name.endswith(".torrent"))
async def add_file_torrent(message: types.Message, bot: Bot):
    user = message.from_user
    log.info(f"[FILE] {_u(user)} | {message.document.file_name}")
    try:
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)
        torrent_content = file_bytes.read()
        result = await qb.add_magnet_file(torrent_content)
        if result == "duplicate":
            await message.reply("⚠️ <b>Этот торрент уже есть в qBittorrent.</b>", parse_mode="HTML")
        elif result:
            await message.reply(f"✅ <b>Файл добавлен!</b>\n📦 <code>{message.document.file_name}</code>", parse_mode="HTML")
        else:
            await message.reply("❌ <b>qBittorrent отклонил файл.</b>", parse_mode="HTML")
    except Exception as e:
        log.error(f"[QBIT] File add error: {e}")
        await message.reply("❌ <b>Ошибка при загрузке файла.</b>", parse_mode="HTML")
