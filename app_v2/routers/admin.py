import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from collections import Counter

import storage.users as user_storage
import config
from services.auth import is_admin

router = Router()
log = logging.getLogger("torrent_bot")

def get_user_link(uid, info):
    username = info.get('username')
    name = info.get('name', info.get('full_name', 'Без имени'))
    if username:
        return f"@{username}"
    return f"<a href='tg://user?id={uid}'>{name}</a>"

async def send_admin_ui(message_or_callback, is_edit=False):
    users = user_storage.load_users()
    msg = "👑 <b>Панель администратора</b>\n───────────────────\n"
    kb = InlineKeyboardBuilder()

    pending = {k: v for k, v in users.items() if v.get('status') == 'pending'}
    active = {k: v for k, v in users.items() if v.get('status') == 'active'}

    msg += f"⏳ <b>Заявки: {len(pending)}</b>\n"
    for uid, info in pending.items():
        name = info.get('full_name', info.get('name', '???'))
        kb.row(types.InlineKeyboardButton(text=f"✅ {name[:15]}", callback_data=f"adm_act_{uid}"))

    msg += f"\n👥 <b>Активные: {len(active)}</b>\n"
    for uid, info in active.items():
        role_icon = "👑" if info.get('role') == 'admin' else "👤"
        msg += f"{role_icon} {get_user_link(uid, info)} <code>({uid})</code>\n"
        name = info.get('full_name', info.get('name', '???'))
        kb.row(types.InlineKeyboardButton(text=f"📂 {name[:15]}", callback_data=f"adm_prof_{uid}"))

    kb.row(types.InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"))

    if is_edit:
        await message_or_callback.message.edit_text(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await message_or_callback.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")

async def send_stats(message_or_callback, is_edit=False):
    import json, os

    # История поиска
    history_path = "/app/app_v2/storage/history.json"
    all_queries = []
    user_query_counts = {}
    users = user_storage.load_users()

    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except:
                history = {}
        for uid, queries in history.items():
            all_queries.extend(queries)
            user_query_counts[uid] = len(queries)

    top_queries = Counter(all_queries).most_common(10)

    msg = "📊 <b>Статистика</b>\n───────────────────\n\n"

    # Топ запросов
    msg += "🔍 <b>Топ запросов:</b>\n"
    if top_queries:
        for i, (query, count) in enumerate(top_queries, 1):
            msg += f"{i}. {query} — <b>{count}x</b>\n"
    else:
        msg += "Нет данных\n"

    # Активность юзеров
    msg += "\n👤 <b>Активность юзеров:</b>\n"
    if user_query_counts:
        sorted_users = sorted(user_query_counts.items(), key=lambda x: -x[1])
        for uid, count in sorted_users:
            info = users.get(str(uid), {})
            name = info.get('full_name', info.get('name', f'uid:{uid}'))
            username = info.get('username')
            tag = f"@{username}" if username else name
            msg += f"{tag} — <b>{count}</b> запросов\n"
    else:
        msg += "Нет данных\n"

    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back"))

    if is_edit:
        await message_or_callback.message.edit_text(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await message_or_callback.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await send_admin_ui(message)

@router.callback_query(F.data == "req_access")
async def cb_req_access(c: types.CallbackQuery, bot: Bot):
    uid = c.from_user.id
    user_data = user_storage.get_user(uid)

    if user_data and user_data.get('status') == 'pending':
        await c.answer("⏳ Запрос уже отправлен ранее!", show_alert=True)
        await c.message.edit_text("⏳ Ваш запрос уже находится на рассмотрении администратора.")
        return

    if user_data and user_data.get('status') == 'active':
        return await c.answer("Вы уже активированы!", show_alert=True)

    new_user = {
        "username": c.from_user.username,
        "full_name": c.from_user.full_name,
        "name": c.from_user.first_name,
        "status": "pending",
        "role": "user"
    }
    await user_storage.set_user(uid, new_user)
    await c.answer("⏳ Заявка отправлена администратору.", show_alert=True)
    await c.message.edit_text("⏳ Ваша заявка находится на рассмотрении у администратора.")

    try:
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text=f"✅ Активировать {c.from_user.first_name}", callback_data=f"adm_act_{uid}"))
        kb.row(types.InlineKeyboardButton(text="👑 В админку", callback_data="adm_back"))
        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"🔔 <b>Новая заявка на доступ!</b>\n\n"
                 f"Пользователь: {get_user_link(uid, new_user)}\n"
                 f"ID: <code>{uid}</code>",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"[ADMIN] Ошибка отправки уведомления админу: {e}")

@router.callback_query(F.data.startswith("adm_"))
async def manage_users(c: types.CallbackQuery, bot: Bot):
    if not is_admin(c.from_user.id):
        return

    parts = c.data.split("_")
    action = parts[1]

    if action == "back":
        return await send_admin_ui(c, is_edit=True)

    if action == "stats":
        return await send_stats(c, is_edit=True)

    if len(parts) < 3:
        return await c.answer("Ошибка данных")

    uid = parts[2]

    if action == "prof":
        if int(uid) == config.ADMIN_ID and c.from_user.id != config.ADMIN_ID:
            return await c.answer("⛔ Нельзя управлять главным администратором.", show_alert=True)

        user_data = user_storage.get_user(int(uid)) or {}
        kb = InlineKeyboardBuilder()

        if int(uid) == c.from_user.id:
            kb.row(types.InlineKeyboardButton(text="⛔ Нельзя менять себя", callback_data="adm_noop"))
        elif int(uid) == config.ADMIN_ID:
            kb.row(types.InlineKeyboardButton(text="⛔ Главный админ защищён", callback_data="adm_noop"))
        else:
            next_role = 'user' if user_data.get('role') == 'admin' else 'admin'
            kb.row(types.InlineKeyboardButton(text="🔄 Сменить роль", callback_data=f"adm_setrole_{next_role}_{uid}"))
            kb.row(types.InlineKeyboardButton(text="🚫 Забанить", callback_data=f"adm_ban_{uid}"))

        kb.row(types.InlineKeyboardButton(text="📋 История поиска", callback_data=f"adm_history_{uid}"))
        kb.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back"))
        await c.message.edit_text(
            f"⚙️ Управление пользователем:\n{get_user_link(uid, user_data)} (<code>{uid}</code>)",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
        return

    if action == "history":
        import json, os
        history_path = "/app/app_v2/storage/history.json"
        target_uid = uid
        user_data = user_storage.get_user(int(target_uid)) or {}
        name = user_data.get('full_name', user_data.get('name', f'uid:{target_uid}'))

        history = {}
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                try:
                    history = json.load(f)
                except:
                    history = {}

        queries = history.get(str(target_uid), [])
        if queries:
            msg = f"🕐 <b>История поиска — {name}:</b>\n\n"
            for i, q in enumerate(queries[:20], 1):
                msg += f"{i}. {q}\n"
        else:
            msg = f"🕐 <b>История поиска — {name}:</b>\n\nПусто"

        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"adm_prof_{target_uid}"))
        await c.message.edit_text(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
        return

    if action == "noop":
        return await c.answer()

    if action == "act":
        await user_storage.update_user(int(uid), {'status': 'active'})
        await c.answer("Пользователь активирован")
        try:
            await bot.send_message(
                chat_id=int(uid),
                text="✅ <b>Доступ разрешён!</b>\n\nДобро пожаловать! Нажмите /start чтобы открыть меню.",
                parse_mode="HTML"
            )
        except Exception as e:
            log.warning(f"[ADMIN] Не удалось уведомить пользователя {uid}: {e}")

    elif action == "ban":
        if int(uid) == c.from_user.id or int(uid) == config.ADMIN_ID:
            return await c.answer("⛔ Это действие запрещено.", show_alert=True)
        await user_storage.update_user(int(uid), {'status': 'banned'})
        await c.answer("Пользователь забанен")
        try:
            await bot.send_message(
                chat_id=int(uid),
                text="🚫 <b>Ваш доступ заблокирован.</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            log.warning(f"[ADMIN] Не удалось уведомить пользователя {uid}: {e}")

    elif action == "setrole":
        role = parts[2]
        target_uid = int(parts[3])
        if target_uid == c.from_user.id:
            return await c.answer("⛔ Нельзя менять роль самому себе.", show_alert=True)
        if target_uid == config.ADMIN_ID:
            return await c.answer("⛔ Нельзя менять роль главного администратора.", show_alert=True)
        await user_storage.update_user(target_uid, {'role': role})
        await c.answer(f"Роль изменена на {role}")
        try:
            await bot.send_message(
                chat_id=target_uid,
                text=f"🔄 Ваша роль изменена на <b>{role}</b>.",
                parse_mode="HTML"
            )
        except Exception as e:
            log.warning(f"[ADMIN] Не удалось уведомить пользователя {target_uid}: {e}")

    await send_admin_ui(c, is_edit=True)

@router.message(F.text == "⚙️ Админка")
async def btn_admin_panel(message: types.Message):
    user = message.from_user
    log.info(f"[BTN] ⚙️ Админка | {user.id} @{user.username}")
    if not is_admin(message.from_user.id):
        return
    await send_admin_ui(message)
