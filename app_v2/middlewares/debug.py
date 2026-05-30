import time
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update

log = logging.getLogger("torrent_bot")


class DebugMiddleware(BaseMiddleware):

    async def __call__(self, handler, event, data):

        start = time.time()

        update: Update = data.get("update") or data.get("event_update") or event

        chat_id = None
        text = None
        callback = None
        update_type = type(update).__name__ if update else None

        if isinstance(update, Update):

            if update.message:
                chat_id = update.message.chat.id
                text = update.message.text

            elif update.callback_query:
                cq = update.callback_query
                chat_id = cq.message.chat.id if cq.message else None
                callback = cq.data
                text = cq.message.text if cq.message else None

        result = await handler(event, data)

        duration = (time.time() - start) * 1000

        log.debug(
            "[UPDATE] type=%s chat_id=%s text=%s callback=%s duration=%.2fms",
            update_type,
            chat_id,
            text,
            callback,
            duration
        )

        return result
