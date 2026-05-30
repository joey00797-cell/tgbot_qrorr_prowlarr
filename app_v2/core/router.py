from aiogram import Router
from routers.menu import router as menu_router
from routers.search import router as search_router
from routers.torrents import router as torrents_router
from routers.admin import router as admin_router
from routers.history import router as history_router
import logging

log = logging.getLogger("torrent_bot")

def setup_routers() -> Router:
    root_router = Router()
    log.info("[ROUTER] include menu")
    root_router.include_router(menu_router)
    log.info("[ROUTER] include torrents")
    root_router.include_router(torrents_router)
    log.info("[ROUTER] include history")
    root_router.include_router(history_router)
    log.info("[ROUTER] include search")
    root_router.include_router(search_router)
    log.info("[ROUTER] include admin")
    root_router.include_router(admin_router)
    return root_router
