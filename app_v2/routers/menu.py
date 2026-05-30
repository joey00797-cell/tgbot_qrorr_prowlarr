import logging
from aiogram import Router, types, F
from aiogram.types import ReplyKeyboardRemove
from aiogram.filters import CommandStart
import keyboards.menu as menu_keyboards
from services.auth import is_admin, is_active, is_pending

router = Router()
log = logging.getLogger("torrent_bot")

def _u(user) -> str:
    un = f"@{user.username}" if user.username else "no_username"
    return f"{user.id} {un}"

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    log.info(f"[MENU] {_u(message.from_user)} | /start")

    if is_admin(uid):
        await message.answer(
            "👋 <b>Добро пожаловать в Медиа-Бот!</b>\n\n"
            "Здесь вы можете искать торренты и управлять загрузками.",
            reply_markup=menu_keyboards.get_main_menu(is_admin=True),
            parse_mode="HTML"
        )
    elif is_active(uid):
        await message.answer(
            "👋 <b>Добро пожаловать в Медиа-Бот!</b>\n\n"
            "Здесь вы можете искать торренты и управлять загрузками.",
            reply_markup=menu_keyboards.get_main_menu(is_admin=False),
            parse_mode="HTML"
        )
    elif is_pending(uid):
        await message.answer(
            "⏳ <b>Заявка на рассмотрении.</b>\n\n"
            "Ожидайте подтверждения администратора.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Для доступа к боту необходимо разрешение администратора.",
            reply_markup=menu_keyboards.get_request_access_keyboard(),
            parse_mode="HTML"
        )

@router.message(F.text == "🏠 Главное меню")
@router.message(F.text == "🔙 В главное меню")
async def cmd_back_to_menu(message: types.Message):
    uid = message.from_user.id
    await message.answer("🏠 Главное меню", reply_markup=menu_keyboards.get_main_menu(is_admin=is_admin(uid)))

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(c: types.CallbackQuery):
    uid = c.from_user.id
    await c.message.delete()
    await c.message.answer(
        "🏠 <b>Главное меню:</b>",
        reply_markup=menu_keyboards.get_main_menu(is_admin=is_admin(uid)),
        parse_mode="HTML"
    )
    await c.answer()
