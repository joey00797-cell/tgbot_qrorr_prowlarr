import asyncio
import logging
from aiogram import Bot
from services.qbittorrent import qb
import storage.users as user_storage
from storage.downloads import get_download, remove_download
from storage.watchlist import get_all_watches, update_size, remove_watch
import config
log = logging.getLogger('torrent_bot')
_notified_hashes = set()
async def _check_updates(bot: Bot):
    watches = get_all_watches()
    if not watches: return
    from services.prowlarr import search as search_prowlarr
    from services.prowlarr import extract_voice
    try:
        torrents = await qb.torrents()
        torrent_map = {t.get('hash', '').lower(): t for t in torrents}
        for hash_id, info in list(watches.items()):
            uid = info.get('uid', config.ADMIN_ID)
            title = info.get('title', '')
            old_size = info.get('size', 0)
            if hash_id not in torrent_map:
                await remove_watch(hash_id)
                log.info(f'[WATCH] Removed: {title[:40]}')
                continue
            # Извлекаем сезон из title (S5E1-8 → S05)
            import re
            season_match = re.search(r'[Ss](\d{1,2})[Ee]', title)
            season = None
            if season_match:
                season = int(season_match.group(1))
            clean_title = title.replace('(обновляемая)', '').strip()            # Очищаем title: убираем (обновляе
            clean_title = re.sub(r'\s*\([^)]*\d{4}[^)]*\)', '', clean_title)            # Уб
            clean_title = re.sub(r'\s*\[[^\]]*\]', '', clean_title)
            clean_title = clean_title.strip()
            voice, _ = extract_voice(title)
            if voice:
                clean_title = f"{clean_title} {voice}"
            if season:
                clean_title = f"{clean_title} S{season:02d}"
            results = await search_prowlarr(clean_title)
            if not results: continue
            best = max(results, key=lambda x: x.get('size', 0))
            new_size = best.get('size', 0)
            if new_size > old_size and old_size > 0:
                log.info(f'[WATCH] Update found: {title[:40]}')
                await update_size(hash_id, new_size)
                from aiogram.types import InlineKeyboardButton
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                kb = InlineKeyboardBuilder()
                kb.row(InlineKeyboardButton(text='Update', callback_data=f'watch_update_{hash_id}'))
                size_diff = round((new_size - old_size) / (1024**3), 2)
                await bot.send_message(chat_id=int(uid), text=f'Update!\n{title[:50]}\n+{size_diff} GB', reply_markup=kb.as_markup())
    except asyncio.TimeoutError:
        log.warning(f'[WATCH] Таймаут для "{clean_title[:40]}" — пропускаем')
    except Exception as ex:
        import traceback
        log.error(f'[WATCH] Error: {ex}')
        log.error(traceback.format_exc())
async def torrent_watchdog_loop(bot: Bot):
    log.info('[WATCHDOG] Loop started')
    await asyncio.sleep(5)
    try:
        torrents = await qb.torrents()
        if torrents:
            for t in torrents:
                if float(t.get('progress', 0)) >= 1.0:
                    _notified_hashes.add(t.get('hash').lower())
            log.info(f'[WATCHDOG] Skipped old: {len(_notified_hashes)}')
    except Exception as e: log.error(f'[WATCHDOG] Init error: {e}')
    while True:
        try:
            torrents = await qb.torrents()
            active = any(t.get('state') in ['downloading', 'metaDL'] for t in torrents) if torrents else False
            sleep_time = 15 if active else 60
            for t in torrents or []:
                progress = float(t.get('progress', 0))
                hash_id = t.get('hash', '').lower()
                name = t.get('name', 'Unknown')
                size_bytes = int(t.get('size', 0))
                if progress >= 1.0 and hash_id not in _notified_hashes:
                    _notified_hashes.add(hash_id)
                    log.info(f'[WATCHDOG] Complete: {name}')
                    size_gb = round(size_bytes / (1024 ** 3), 2)
                    dl_info = await get_download(hash_id)
                    if dl_info:
                        notify = dl_info.get('notify', 'me')
                        owner_uid = int(dl_info.get('uid', config.ADMIN_ID))
                        await remove_download(hash_id)
                    else:
                        notify = 'me'
                        owner_uid = int(config.ADMIN_ID)
                    text = f'🎬 <b>Скачано!</b>\n\n📦 {name}\n💾 {size_gb} GB\n\n🍿 Приятного просмотра!'
                    if notify == 'me':
                        try: await bot.send_message(chat_id=owner_uid, text=text, parse_mode="HTML")
                        except Exception: pass
                        if owner_uid != int(config.ADMIN_ID):
                            user_data = user_storage.get_user(owner_uid)
                            username = user_data.get('username', 'Unknown') if user_data else 'Unknown'
                            await bot.send_message(chat_id=int(config.ADMIN_ID), text=f'User @{username} downloaded:\n{text}')
                    elif notify == 'all':
                        active_users = user_storage.get_all_active_users()
                        for u in active_users:
                            try: await bot.send_message(chat_id=int(u['user_id']), text=text, parse_mode="HTML")
                            except Exception: pass
            await _check_updates(bot)
        except Exception as ex: log.error(f'[WATCHDOG] Loop error: {ex}')
        await asyncio.sleep(sleep_time)
