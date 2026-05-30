import re

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from aiogram.utils.keyboard import InlineKeyboardBuilder


def generate_search_page(
    results,
    page=1,
    per_page=5,
    search_query=None
):

    total = len(results)

    start = (page - 1) * per_page
    end = start + per_page

    sliced = results[start:end]

    total_pages = (
        (total + per_page - 1) // per_page
        if total > 0 else 1
    )

    text = (
        f"🔍 <b>Результаты "
        f"(Стр. {page}/{total_pages})</b>\n\n"
    )

    kb = InlineKeyboardBuilder()

    for i, item in enumerate(sliced, start=start + 1):

        seeds = item.get("seeders", 0)
        peers = item.get("leechers", 0)

        size_gb = round(
            item.get("size", 0) / (1024 ** 3),
            2
        )

        title = item.get("title", "NO TITLE")

        tracker = item.get("indexer", "Tracker")

        text += (
            f"<b>{i}) {title}</b>\n"
            f"{size_gb} GB | "
            f"↑ {seeds} ↓ {peers} | "
            f"{tracker}\n\n"
        )

        kb.add(
            InlineKeyboardButton(
                text=str(i),
                callback_data=f"view_{i}_{page}"
            )
        )

    kb.adjust(5)

    nav = []

    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"page_{page-1}"
            )
        )

    if end < total:
        nav.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"page_{page+1}"
            )
        )

    if nav:
        kb.row(*nav)

    return text, kb.as_markup()


def generate_detail_page(item, idx, page):

    size_gb = round(
        item.get("size", 0) / (1024 ** 3),
        2
    )

    text = (
        f"📄 <b>{item['title']}</b>\n\n"
        f"💾 {size_gb} GB\n"
        f"🌱 Сиды: {item.get('seeders', 0)}\n"
        f"📡 Пиры: {item.get('leechers', 0)}"
    )

    kb = InlineKeyboardBuilder()

    kb.row(
        InlineKeyboardButton(
            text="📥 Скачать",
            callback_data=f"dl_{idx}"
        )
    )

    kb.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"page_{page}"
        )
    )

    return text, kb.as_markup()
