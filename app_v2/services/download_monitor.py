import asyncio
import logging

log = logging.getLogger("torrent_bot")

async def start_download_monitor():
    log.info("[MONITOR] Инициализация мониторинга загрузок...")
    from services.qbittorrent import qb
    
    while True:
        try:
            # Здесь твоя логика проверки статусов
            await asyncio.sleep(60)
        except Exception as e:
            log.error(f"[MONITOR] Ошибка: {e}")
            await asyncio.sleep(60)
