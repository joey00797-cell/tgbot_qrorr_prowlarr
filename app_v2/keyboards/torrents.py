from aiogram.types import (
    InlineKeyboardButton
)

from aiogram.utils.keyboard import (
    InlineKeyboardBuilder
)


def torrents_menu(
    torrents,
    page=1,
    per_page=10
):

    kb = InlineKeyboardBuilder()

    start = (page - 1) * per_page
    end = start + per_page

    sliced = torrents[start:end]

    for i, torrent in enumerate(
        sliced,
        start=start + 1
    ):

        kb.add(
            InlineKeyboardButton(
                text=str(i),
                callback_data=(
                    f"torrent_{i}"
                )
            )
        )

    kb.adjust(5)

    nav = []

    if page > 1:

        nav.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=(
                    f"qpage_{page-1}"
                )
            )
        )

    if end < len(torrents):

        nav.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=(
                    f"qpage_{page+1}"
                )
            )
        )

    if nav:
        kb.row(*nav)

    kb.row(
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=(
                f"qpage_{page}"
            )
        )
    )

    return kb.as_markup()
