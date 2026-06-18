from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

def get_main_menu(is_admin: bool = False):
    keyboard = [
        [KeyboardButton(text="🔍 Поиск торрентов"), KeyboardButton(text="🎬 Подобрать фильм")],
        [
            KeyboardButton(text="📥 Добавить торрент"),
            KeyboardButton(text="📊 Статус закачек")
        ]
    ]
    if is_admin:
        keyboard.append([
            KeyboardButton(text="⚙️ Админка"),
            KeyboardButton(text="🔧 Настройки"),
        ])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_request_access_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🔑 Запросить доступ", callback_data="req_access")
        ]]
    )
