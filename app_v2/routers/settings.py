import logging
import subprocess
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

router = Router()
log = logging.getLogger("torrent_bot")

MENU_BUTTON = "🔧 Настройки"

def build_settings_menu():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💾 Статус дисков", callback_data="settings_disk"))
    kb.row(InlineKeyboardButton(text="🧹 Очистить кеш Jellyfin", callback_data="settings_clean_cache"))
    kb.row(InlineKeyboardButton(text="🐳 Docker prune", callback_data="settings_docker_prune"))
    kb.row(InlineKeyboardButton(text="🔄 Перезапустить бота", callback_data="settings_restart_bot"))
    kb.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return kb.as_markup()

@router.message(F.text == MENU_BUTTON)
async def settings_menu(message: types.Message):
    await message.answer(
        "🔧 <b>Настройки и управление</b>",
        reply_markup=build_settings_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "settings_disk")
async def settings_disk(c: types.CallbackQuery):
    await c.message.edit_text("⏳ <b>Считываю данные дисков...</b>", parse_mode="HTML")
    try:
        import aiohttp as _aiohttp
        async with _aiohttp.ClientSession() as s:
            async with s.get("http://192.168.31.206:9999", timeout=_aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()

        def fmt(d):
            total = d["total"] // (1024**3)
            used  = d["used"]  // (1024**3)
            pct   = int(d["used"] / d["total"] * 100)
            bar   = "█" * (pct // 10) + "░" * (10 - pct // 10)
            return f"{bar} {pct}%\n{used}G / {total}G"

        text = (f"💾 <b>Статус дисков</b>\n\n"
                f"🖥 <b>Arr-стак:</b>\n{fmt(data['arr'])}\n\n"
                f"📁 <b>Медиа:</b>\n{fmt(data['media'])}")

        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="settings_disk"))
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back"))
        await c.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception as e:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back"))
        await c.message.edit_text(
            f"⚠️ <b>Ошибка получения данных</b>\n\n"
            f"Убедись что status-server запущен на 192.168.31.206:9999\n<code>{str(e)[:100]}</code>",
            reply_markup=kb.as_markup(), parse_mode="HTML"
        )

@router.callback_query(F.data == "settings_clean_cache")
async def settings_clean_cache(c: types.CallbackQuery):
    try:
        import shutil, os
        paths = [
            "/opt/stacks/arr-stack/config/jellyfin/cache/transcodes",
            "/opt/stacks/arr-stack/config/jellyfin/data/transcodes",
        ]
        cleaned = 0
        for p in paths:
            if os.path.exists(p):
                for f in os.listdir(p):
                    fp = os.path.join(p, f)
                    try:
                        if os.path.isfile(fp):
                            size = os.path.getsize(fp)
                            os.remove(fp)
                            cleaned += size
                        elif os.path.isdir(fp):
                            size = sum(os.path.getsize(os.path.join(dirpath, f))
                                      for dirpath, _, files in os.walk(fp) for f in files)
                            shutil.rmtree(fp)
                            cleaned += size
                    except:
                        pass
        cleaned_mb = cleaned // (1024**2)
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back"))
        await c.message.edit_text(
            f"🧹 <b>Кеш Jellyfin очищен</b>\n\nОсвобождено: {cleaned_mb} MB",
            reply_markup=kb.as_markup(), parse_mode="HTML"
        )
        log.info(f"[SETTINGS] {c.from_user.id} очистил кеш Jellyfin: {cleaned_mb} MB")
    except Exception as e:
        await c.answer(f"Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "settings_docker_prune")
async def settings_docker_prune(c: types.CallbackQuery):
    await c.message.edit_text("⏳ Выполняю docker prune...", parse_mode="HTML")
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "system", "prune", "-f"],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()[-200:] if result.stdout else "Нет вывода"
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back"))
        await c.message.edit_text(
            f"🐳 <b>Docker prune выполнен</b>\n\n<code>{output}</code>",
            reply_markup=kb.as_markup(), parse_mode="HTML"
        )
        log.info(f"[SETTINGS] {c.from_user.id} выполнил docker prune")
    except Exception as e:
        await c.answer(f"Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "settings_restart_bot")
async def settings_restart_bot(c: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Да, перезапустить", callback_data="settings_restart_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="settings_back"),
    )
    await c.message.edit_text(
        "⚠️ <b>Перезапустить бота?</b>\n\nСессия прервётся на несколько секунд.",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )

@router.callback_query(F.data == "settings_restart_confirm")
async def settings_restart_confirm(c: types.CallbackQuery):
    await c.message.edit_text("🔄 <b>Перезапускаю...</b>", parse_mode="HTML")
    log.info(f"[SETTINGS] {c.from_user.id} перезапустил бота")
    import asyncio, os, signal
    await asyncio.sleep(1)
    os.kill(os.getpid(), signal.SIGTERM)

@router.callback_query(F.data == "settings_back")
async def settings_back(c: types.CallbackQuery):
    await c.message.edit_text(
        "🔧 <b>Настройки и управление</b>",
        reply_markup=build_settings_menu(),
        parse_mode="HTML"
    )
