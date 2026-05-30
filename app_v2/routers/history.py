import logging
from aiogram import Router, types, F
from aiogram.types import LinkPreviewOptions, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from storage.history import get_history
from services.prowlarr import search as search_prowlarr

router = Router()
log = logging.getLogger("torrent_bot")

# Импортируем из search чтобы не дублировать логику
from routers.search import (
    search_results_cache,
    local_generate_search_page,
)

PER_PAGE = 10

def build_history_keyboard(uid: int, page: int = 1):
    history = get_history(uid)
    total = len(history)
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    sliced = history[start:end]
    total_pages = (total + PER_PAGE - 1) // PER_PAGE if total > 0 else 1

    text = f"🕐 <b>История поиска (Стр. {page} из {total_pages}):</b>\n\n"
    for i, query in enumerate(sliced, start=start+1):
        text += f"{i}. {query}\n"

    kb = InlineKeyboardBuilder()
    # Кнопки с номерами — 2 ряда по 5
    buttons = []
    for i, _ in enumerate(sliced, start=start+1):
        buttons.append(InlineKeyboardButton(
            text=str(i),
            callback_data=f"hist_pick_{i-1}_{page}"
        ))
    kb.add(*buttons)
    kb.adjust(5)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"hist_page_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"hist_page_{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="hist_back"))

    return text, kb.as_markup()


@router.callback_query(F.data == "show_history")
async def show_history(c: types.CallbackQuery):
    uid = c.from_user.id
    history = get_history(uid)

    if not history:
        return await c.answer("История пуста — сначала что-нибудь поищи.", show_alert=True)

    text, markup = build_history_keyboard(uid, page=1)
    await c.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("hist_page_"))
async def hist_paginate(c: types.CallbackQuery):
    page = int(c.data.split("_")[2])
    text, markup = build_history_keyboard(c.from_user.id, page=page)
    try:
        await c.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await c.answer()


@router.callback_query(F.data.startswith("hist_pick_"))
async def hist_pick(c: types.CallbackQuery):
    parts = c.data.split("_")
    idx = int(parts[2])

    history = get_history(c.from_user.id)
    if idx >= len(history):
        return await c.answer("Запись не найдена.", show_alert=True)

    query = history[idx]
    log.info(f"[HISTORY] {c.from_user.id} повторяет поиск: \"{query}\"")

    await c.message.edit_text(f"⏳ Ищу: <i>{query}</i>...", parse_mode="HTML")

    try:
        raw_results = await search_prowlarr(query)
        results = sorted(raw_results, key=lambda x: int(x.get("seeders", 0)), reverse=True)
        search_results_cache[c.from_user.id] = {"results": results, "query": query}

        if not results:
            await c.message.edit_text("❌ Ничего не найдено.")
            return

        text, markup = local_generate_search_page(results, page=1, search_query=query)
        await c.message.edit_text(text, reply_markup=markup, parse_mode="HTML",
                                  disable_web_page_preview=True)
    except Exception as ex:
        log.error(f"[HISTORY] Ошибка поиска: {ex}")
        await c.message.edit_text(f"⚠️ Ошибка поиска:\n{str(ex)[:100]}", parse_mode="HTML")


@router.callback_query(F.data == "hist_back")
async def hist_back(c: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🕐 История", callback_data="show_history"))
    await c.message.edit_text(
        "🔍 <b>Поиск торрентов</b>\n\n"
        "Напиши название фильма, сериала или любого контента.\n\n"
        "💡 Можно уточнить запрос:\n"
        "• <code>Пацаны сезон 3</code> — конкретный сезон\n"
        "• <code>Пацаны лостфильм</code> — конкретная озвучка\n"
        "• <code>!бот</code> — принудительный поиск (обход болталки)",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
