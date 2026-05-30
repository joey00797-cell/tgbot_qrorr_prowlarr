import logging
from aiogram import Dispatcher
from aiogram.types import ErrorEvent

log = logging.getLogger("torrent_bot")

def create_dispatcher(bot=None) -> Dispatcher:
    dp = Dispatcher()

    @dp.errors()
    async def errors_handler(event: ErrorEvent):
        # Логируем реальную ошибку, которая произошла в боте или сервисах
        log.error(f"[AIOGRAM_ERROR] err={event.exception}", exc_info=event.exception)
        return True

    async def on_startup():
        log.info("=== STARTUP HOOK ===")

    dp.startup.register(on_startup)
    return dp
