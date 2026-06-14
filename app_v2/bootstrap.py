import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config.settings import TELEGRAM_TOKEN
from middlewares.auth import AuthMiddleware
from services.watchdog import torrent_watchdog_loop
from storage.database import init_db
from storage.watchlist import init_watchlist
from storage.history import init_history
import routers.menu as menu_module
import routers.torrents as torrents_module
import routers.search as search_module
import routers.admin as admin_module
import routers.history as history_module
import routers.settings as settings_module

log = logging.getLogger("torrent_bot")

async def on_startup(bot: Bot):
    log.info("🚀 Начинаю инициализацию системных служб...")
    try:
        await init_db()
        await init_watchlist()
        await init_history()
        log.info("  ├── [ OK ]   База данных SQLite      🗄️ (storage/bot.db)")
    except Exception as e:
        log.error(f"  ├── [ERROR]  Ошибка базы данных: {e}")
        
    # qBittorrent
    try:
        from services.qbittorrent import qb
        await qb.login()
        log.info("  ├── [ OK ]   qBittorrent             🔩 (services/qbittorrent.py)")
    except Exception as e:
        log.error(f"  ├── [ERROR]  qBittorrent: {e}")

    # Prowlarr
    try:
        import aiohttp
        import config as _config
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{_config.PROWLARR_BASE_URL}/api/v1/system/status",
                             headers={"X-Api-Key": _config.PROWLARR_API_KEY}) as r:
                if r.status == 200:
                    log.info("  ├── [ OK ]   Prowlarr               🔍 (services/prowlarr.py)")
                else:
                    log.warning(f"  ├── [WARN]  Prowlarr: status {r.status}")
    except Exception as e:
        log.error(f"  ├── [ERROR]  Prowlarr: {e}")

    # Radarr
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{_config.RADARR_URL}/api/v3/system/status",
                             headers={"X-Api-Key": _config.RADARR_KEY}) as r:
                if r.status == 200:
                    log.info("  ├── [ OK ]   Radarr                 🎬 (services/arrs.py)")
                else:
                    log.warning(f"  ├── [WARN]  Radarr: status {r.status}")
    except Exception as e:
        log.error(f"  ├── [ERROR]  Radarr: {e}")

    # Sonarr
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{_config.SONARR_URL}/api/v3/system/status",
                             headers={"X-Api-Key": _config.SONARR_KEY}) as r:
                if r.status == 200:
                    log.info("  ├── [ OK ]   Sonarr                 📺 (services/arrs.py)")
                else:
                    log.warning(f"  ├── [WARN]  Sonarr: status {r.status}")
    except Exception as e:
        log.error(f"  ├── [ERROR]  Sonarr: {e}")

    asyncio.create_task(torrent_watchdog_loop(bot))
    log.info("  ├── [ OK ]   Служба Watchdog запущен  🛰️ (services/watchdog.py)")
    log.info("  └── [SUCCESS] Бот успешно запущен и готов к работе! 🤖")

def register_all_routers(dp: Dispatcher):
    log.info("🚀 Начинаю загрузку компонентов и роутеров...")
    modules_to_load = [
        (menu_module.router,     "Главное меню",          menu_module.__name__),
        (admin_module.router,    "Панель администратора", admin_module.__name__),
        (torrents_module.router, "Управление торрентами", torrents_module.__name__),
        (history_module.router,  "История поиска",        history_module.__name__),
        (settings_module.router, "Настройки",             settings_module.__name__),
        (search_module.router,   "Поиск Prowlarr",        search_module.__name__),
    ]
    for router, name, mod_name in modules_to_load:
        try:
            dp.include_router(router)
            log.info(f"  ├── [LOADED] {name:<23} 📦 ({mod_name}.py)")
        except Exception as e:
            log.error(f"  └── [ERROR]  Ошибка загрузки модуля {name}: {e}")
    log.info("✅ Все роутеры успешно привязаны к диспетчеру aiogram!")

def create_app():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(AuthMiddleware())
    register_all_routers(dp)
    dp.startup.register(on_startup)
    return bot, dp
