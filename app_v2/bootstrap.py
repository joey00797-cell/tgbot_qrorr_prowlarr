import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config.settings import TELEGRAM_TOKEN
from middlewares.auth import AuthMiddleware
from services.watchdog import torrent_watchdog_loop
import routers.menu as menu_module
import routers.torrents as torrents_module
import routers.search as search_module
import routers.admin as admin_module
import routers.history as history_module

log = logging.getLogger("torrent_bot")

async def on_startup(bot: Bot):
    asyncio.create_task(torrent_watchdog_loop(bot))
    log.info("✅ Watchdog запущен!")

def register_all_routers(dp: Dispatcher):
    log.info("🚀 Начинаю загрузку компонентов и роутеров...")
    modules_to_load = [
        (menu_module.router,     "Главное меню",          menu_module.__name__),
        (admin_module.router,    "Панель администратора", admin_module.__name__),
        (torrents_module.router, "Управление торрентами", torrents_module.__name__),
        (history_module.router,  "История поиска",        history_module.__name__),
        (search_module.router,   "Поиск Prowlarr",        search_module.__name__),
    ]
    for router, name, mod_name in modules_to_load:
        try:
            dp.include_router(router)
            log.info(f"  ├── [LOADED] {name:<23} 📦 ({mod_name}.py)")
        except Exception as e:
            log.error(f"  └── [ERROR]  Ошибка загрузки модуля {name}: {e}")
    log.info("✅ Все модули успешно привязаны к диспетчеру aiogram!")

def create_app():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(AuthMiddleware())
    dp.startup.register(on_startup)
    register_all_routers(dp)
    return bot, dp
