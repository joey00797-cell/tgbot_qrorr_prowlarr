import asyncio
from utils.logger import setup_logger
setup_logger()

from bootstrap import create_app

import logging
log = logging.getLogger("torrent_bot")

async def main():
    log.info("ENTRYPOINT START")
    bot, dp = create_app()
    log.info("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
