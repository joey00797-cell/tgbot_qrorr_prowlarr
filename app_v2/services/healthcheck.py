import aiohttp
import logging

import config

log = logging.getLogger(
    "torrent_bot"
)


async def check_qbittorrent():

    try:

        async with aiohttp.ClientSession() as session:

            url = (
                f"http://{config.QBIT_HOST}:"
                f"{config.QBIT_PORT}"
                f"/api/v2/app/version"
            )

            async with session.get(
                url,
                timeout=10
            ) as resp:

                text = await resp.text()

                log.info(
                    f"[QBIT] ONLINE | "
                    f"version={text}"
                )

                return True

    except Exception as e:

        log.error(
            f"[QBIT] OFFLINE | {e}"
        )

        return False


async def check_prowlarr():

    try:

        async with aiohttp.ClientSession() as session:

            url = (
                f"{config.PROWLARR_BASE_URL}"
                f"/api/v1/indexer"
            )

            headers = {
                "X-Api-Key":
                config.PROWLARR_API_KEY
            }

            async with session.get(
                url,
                headers=headers,
                timeout=10
            ) as resp:

                data = await resp.json()

                log.info(
                    f"[PROWLARR] ONLINE | "
                    f"indexers={len(data)}"
                )

                return True

    except Exception as e:

        log.error(
            f"[PROWLARR] OFFLINE | {e}"
        )

        return False


async def run_healthchecks():

    log.info(
        "Running service checks..."
    )

    await check_qbittorrent()

    await check_prowlarr()

    log.info(
        "Healthchecks completed"
    )
