import time
from typing import Any, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import logging
from services.auth import is_admin, is_active, is_pending

log = logging.getLogger("torrent_bot")

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: TelegramObject, data: Dict[str, Any]) -> Any:
        start = time.time()

        user = None
        if hasattr(event, "message") and event.message:
            user = event.message.from_user
        elif hasattr(event, "callback_query") and event.callback_query:
            user = event.callback_query.from_user

        if not user:
            return await handler(event, data)

        uid = user.id
        admin = is_admin(uid)
        active = is_active(uid)

        text = ""
        if hasattr(event, "message") and event.message:
            text = event.message.text or ""
        cb = ""
        if hasattr(event, "callback_query") and event.callback_query:
            cb = event.callback_query.data or ""

        username = f"@{user.username}" if user.username else "no_username"

        blocked = False
        if not admin:
            if text == "/start" and not is_pending(uid):
                pass
            elif text and is_active(uid):
                pass
            elif cb == "req_access":
                pass
            elif cb and is_active(uid):
                pass
            else:
                blocked = True

        if blocked:
            if hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.answer("🚫 Нет доступа", show_alert=True)
            duration = int((time.time() - start) * 1000)
            payload = repr(cb) if cb else repr(text[:60]) if text else "''"
            log.warning(f"[AUTH] {uid} {username} | BLOCKED | {payload} | {duration}ms")
            return

        return await handler(event, data)
