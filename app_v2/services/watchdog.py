import asyncio
import logging
from aiogram import Bot
from services.qbittorrent import qb
import storage.users as user_storage
from storage.downloads import get_download, remove_download
from storage.watchlist import get_all_watches, update_size, remove_watch
import config

log = logging.getLogger("torrent_bot")
_notified_hashes = set()

async def _check_updates(bot: Bot):
    """Проверяем обновления для торрентов в watchlist."""
    watches = get_all_watches()
    if not watches:
        return

    from services.prowlarr import search as search_prowlarr

    torrents = await qb.torrents()
    torrent_map = {t.get("hash", "").lower(): t for t in torrents}

    for hash_id, info in list(watches.items()):
        uid = info.get("uid", config.ADMIN_ID)
        title = info.get("title", "")
        old_size = info.get("size", 0)

        # Если торрент удалён из qBit — убираем из watchlist
        if hash_id not in torrent_map:
            await remove_watch(hash_id)
            log.info(f"[WATCH] Торрент удалён из qBit, убираем из watchlist: {title[:40]}")
            continue

        # Ищем в Prowlarr свежую раздачу
        try:
            clean_title = title.split('(')[0].replace('(обновляемая)', '').strip()
            results = await search_prowlarr(clean_title)
            if not results:
                continue

            # Берём самую свежую раздачу с максимальным размером
            best = max(results, key=lambda x: x.get("size", 0))
            new_size = best.get("size", 0)

            if new_size > old_size and old_size > 0:
                log.info(f"[WATCH] Обновление найдено: {title[:40]} | {old_size} → {new_size}")
                await update_size(hash_id, new_size)

                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                from aiogram.utils.keyboard import InlineKeyboardBuilder

                kb = InlineKeyboardBuilder()
                kb.row(InlineKeyboardButton(
                    text="🔄 Обновить раздачу",
                    callback_data=f"watch_update_{hash_id}"
                ))
                kb.row(InlineKeyboardButton(
                    text="⏹ Не следить",
                    callback_data=f"watch_stop_{hash_id}"
                ))

                size_diff = round((new_size - old_size) / (1024**3), 2)
                await bot.send_message(
                    chat_id=int(uid),
                    text=f"🔄 <b>Обновление раздачи!</b>\n\n"
                         f"📦 <code>{title[:50]}</code>\n"
                         f"📈 Размер увеличился на +{size_diff} GB",
                    reply_markup=kb.as_markup(),
                    parse_mode="HTML"
                )
                # Уведомляем и админа если это не он
                if int(uid) != int(config.ADMIN_ID):
                    await bot.send_message(
                        chat_id=int(config.ADMIN_ID),
                        text=f"🔄 <b>Обновление раздачи!</b>\n\n"
                             f"📦 <code>{title[:50]}</code>\n"
                             f"📈 +{size_diff} GB",
                        parse_mode="HTML"
                    )
        except Exception as ex:
            log.error(f"[WATCH] Ошибка проверки обновления {title[:30]}: {ex}")

async def torrent_watchdog_loop(bot: Bot):
    log.info("[WATCHDOG] Инициализация фоновой службы слежения...")
    await asyncio.sleep(5)

    try:
        torrents = await qb.torrents()
        if torrents:
            for t in torrents:
                if float(t.get("progress", 0)) >= 1.0:
                    _notified_hashes.add(t.get("hash"))
            log.info(f"[WATCHDOG] Первичный проход. Пропущено старых: {len(_notified_hashes)}")
    except Exception as e:
        log.error(f"[WATCHDOG] Ошибка первичного прохода: {e}")

    check_counter = 0

    while True:
        try:
            torrents = await qb.torrents()
            if torrents:
                active = any(t.get("state") in ["downloading", "metaDL"] for t in torrents)
                sleep_time = 15 if active else 60
            else:
                sleep_time = 60

            for t in torrents or []:
                progress = float(t.get("progress", 0))
                hash_id = t.get("hash", "").lower()
                name = t.get("name", "Unknown")
                size_bytes = int(t.get("size", 0))

                if progress >= 1.0 and hash_id not in _notified_hashes:
                    _notified_hashes.add(hash_id)
                    log.info(f"[WATCHDOG] ✅ Завершена загрузка: {name}")

                    size_gb = round(size_bytes / (1024 ** 3), 2)
                    dl_info = get_download(hash_id)

                    if dl_info:
                        notify = dl_info.get("notify", "me")
                        owner_uid = int(dl_info.get("uid", config.ADMIN_ID))
                        remove_download(hash_id)
                    else:
                        notify = "me"
                        owner_uid = int(config.ADMIN_ID)

                    notify_label = "🔔 Только тебе" if notify == "me" else "📢 Всем"
                    text = (
                        f"✅ <b>Закачка завершена!</b>\n\n"
                        f"📦 <code>{name}</code>\n"
                        f"💾 {size_gb} GB | {notify_label}\n\n"
                        f"Приятного просмотра! 🎬"
                    )

                    recipients = []
                    if notify == "all":
                        try:
                            users = user_storage.load_users()
                            for uid, info in users.items():
                                if info.get("status") == "active":
                                    recipients.append(int(uid))
                        except Exception as ex:
                            log.error(f"[WATCHDOG] Ошибка чтения юзеров: {ex}")
                    else:
                        recipients.append(owner_uid)

                    admin_id = int(config.ADMIN_ID)
                    if admin_id not in recipients:
                        recipients.append(admin_id)

                    for chat_id in recipients:
                        try:
                            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                            await asyncio.sleep(0.05)
                        except Exception:
                            pass

        except Exception as e:
            log.error(f"[WATCHDOG] Ошибка: {e}")
            sleep_time = 60  # При ошибке ждём дольше

        # Проверяем обновления раз в час (3600 / sleep_time итераций)
        check_counter += 1
        if check_counter >= (3600 // max(sleep_time, 15)):
            check_counter = 0
            try:
                await _check_updates(bot)
            except Exception as ex:
                log.error(f"[WATCHDOG] Ошибка проверки обновлений: {ex}")

        await asyncio.sleep(sleep_time)
