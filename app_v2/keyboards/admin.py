from aiogram.types import (
    InlineKeyboardButton
)

from aiogram.utils.keyboard import (
    InlineKeyboardBuilder
)


def admin_panel_keyboard(pending):

    kb = InlineKeyboardBuilder()

    for uid, user in pending.items():

        name = (
            user.get("full_name")
            or "Unknown"
        )

        kb.row(
            InlineKeyboardButton(
                text=f"✅ {name[:20]}",
                callback_data=f"approve_{uid}"
            ),

            InlineKeyboardButton(
                text="❌",
                callback_data=f"reject_{uid}"
            )
        )

    return kb.as_markup()
