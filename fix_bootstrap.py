import re

path = '/opt/torrent-bot/app_v2/bootstrap.py'
content = open(path, 'r', encoding='utf-8').read()

new_code = """async def on_startup(bot: Bot):
    try:
        from storage.database import init_db
        await init_db()
        log.info("✅ База SQLite готова!")
    except Exception as e:
cat << 'EOF' > /opt/torrent-bot/app_v2/bootstrap.py
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config.settings import TELEGRAM_TOKEN
from middlewares.auth import AuthMiddleware
from services.watchdog import torrent_watchdog_loop
from storage.database import init_db
import routers.menu as menu_module
import routers.torrents as torrents_module
import routers.search as search_module
import routers.admin as admin_module
import routers.history as history_module

log = logging.getLogger("torrent_bot")

async def on_startup(bot: Bot):
    try:
        await init_db()
    except Exception as e:        log.info("✅ База SQLite 
        log.error(f"❌ Ошибк�    asyncio.create_task(torrent_watchdog_loop(bot))� БД: {e}")
    asyncio.create_task(torrent_watchdog_loop(bot))
    log.info("✅ Watchdog запущен!")

def register_all_routers(dp: Dispatcher):
    modules = [    log.info("🚀 Загрузка роуте
        (menu_module.router, "Меню", menu_module.__name__),
        (admin_module.router, "Админка", admin_module.__name__),
        (torrents_module.router, "Торренты", torrents_module.__name__),
        (history_module.router, "История", history_module.__name__),
        (search_module.router, "Поиск", search_module.__name__),
    ]
    for router, name, mod_name in modules:
        try:
            dp.include_router(router)
            log.info(f"  ├── [LOADED] {name:<10} 📦 ({mod_name})")
        except Exception as e:
            log.error(f"  └── [ERROR] {name}: {e}")
    log.info("✅ Моди диспетчера при
def create_app():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(AuthMiddleware())
    dp.startup.register(on_startup)
    register_all_routers(dp)
    return bot, dp
