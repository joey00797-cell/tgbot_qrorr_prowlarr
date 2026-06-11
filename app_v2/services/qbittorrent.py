import aiohttp
import logging
import config
import json

log = logging.getLogger("torrent_bot")

class QBittorrentClient:
    def __init__(self):
        self.base_url = f"http://{config.QBIT_HOST}:{config.QBIT_PORT}"
        self.session = None
        self.cookie = None

    async def ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def login(self):
        await self.ensure_session()
        if self.cookie:
            return
        url = f"{self.base_url}/api/v2/auth/login"
        data = aiohttp.FormData()
        data.add_field('username', config.QBIT_USER)
        data.add_field('password', config.QBIT_PASSWORD)
        headers = {
            "Referer": self.base_url,
            "Origin": self.base_url,
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        log.info(f"[QBIT] AUTH -> {self.base_url}")
        try:
            async with self.session.post(url, data=data, headers=headers) as resp:
                log.info(f"[QBIT] LOGIN STATUS: {resp.status}")
                if resp.status not in [200, 204]:
                    text = await resp.text()
                    raise Exception(f"Auth failed with status {resp.status}: {text}")
                cookies = resp.headers.getall('Set-Cookie', [])
                for c in cookies:
                    if 'QBT_SID' in c or 'SID' in c:
                        self.cookie = c.split(';')[0]
                        log.info(f"[QBIT] Saved cookie: {self.cookie}")
                        break
        except Exception as e:
            self.cookie = None
            # Закрываем битую сессию чтобы пересоздать при следующем запросе
            try:
                if self.session and not self.session.closed:
                    await self.session.close()
            except Exception:
                pass
            self.session = None
            log.error(f"[QBIT] Connection error during login: {e}")
            raise e

    async def torrents(self):
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/info"
        headers = {"Cookie": self.cookie} if self.cookie else {}
        async with self.session.get(url, headers=headers) as resp:
            if resp.status in [401, 403]:
                self.cookie = None
                await self.login()
                headers = {"Cookie": self.cookie} if self.cookie else {}
                async with self.session.get(url, headers=headers) as retry_resp:
                    return await retry_resp.json()
            return await resp.json()

    async def add_magnet(self, torrent_url: str, category: str = None, paused: bool = False) -> bool:
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/add"

        with aiohttp.MultipartWriter('form-data') as mpwriter:
            if torrent_url.startswith("magnet:"):
                log.info("[QBIT] Добавление через Magnet-URL")
                part = mpwriter.append(torrent_url)
                part.set_content_disposition('form-data', name='urls')
            else:
                log.info(f"[QBIT] Скачивание .torrent файла: {torrent_url[:60]}")
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as ds:
                        async with ds.get(torrent_url) as file_resp:
                            if file_resp.status == 200:
                                file_content = await file_resp.read()
                                part = mpwriter.append(file_content, headers={'Content-Type': 'application/x-bittorrent'})
                                part.set_content_disposition('form-data', name='torrents', filename='file.torrent')
                            else:
                                log.warning(f"[QBIT] Не удалось скачать файл (HTTP {file_resp.status}), шлем как URL")
                                part = mpwriter.append(torrent_url)
                                part.set_content_disposition('form-data', name='urls')
                except Exception as e:
                    log.error(f"[QBIT] Ошибка скачивания: {e}, шлем как URL")
                    part = mpwriter.append(torrent_url)
                    part.set_content_disposition('form-data', name='urls')

            if category:
                cat_part = mpwriter.append(category)
                cat_part.set_content_disposition('form-data', name='category')

            if paused:
                p_part = mpwriter.append("true")
                p_part.set_content_disposition('form-data', name='paused')
                s_part = mpwriter.append("true")
                s_part.set_content_disposition('form-data', name='stopped')

            headers = {}
            if self.cookie:
                headers["Cookie"] = self.cookie
            headers.update(mpwriter.headers)

            async with self.session.post(url, data=mpwriter, headers=headers) as resp:
                body = await resp.text()
                log.info(f"[QBIT] ADD -> статус={resp.status} тело={body.strip()[:80]}")
                if resp.status in [200, 204]:
                    if body.strip().startswith("{"):
                        try:
                            res_json = json.loads(body)
                            if res_json.get("success_count", 0) > 0:
                                ids = res_json.get("added_torrent_ids", [])
                                return ids[0] if ids else True
                            if res_json.get("failure_count", 0) > 0 or "Fails" in body:
                                return False
                        except Exception:
                            pass
                    if "Fails" in body or "fail" in body.lower():
                        return False
                    return True
                if resp.status == 409:
                    return "duplicate"
                return False

    async def add_magnet_file(self, file_content: bytes, category: str = None, paused: bool = False) -> bool:
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/add"
        data = aiohttp.FormData()
        data.add_field("torrents", file_content, filename="file.torrent", content_type="application/x-bittorrent")
        if category:
            data.add_field("category", category)
        if paused:
            data.add_field("paused", "true")
            data.add_field("stopped", "true")
        headers = {"Cookie": self.cookie} if self.cookie else {}
        async with self.session.post(url, data=data, headers=headers) as resp:
            body = await resp.text()
            log.info(f"[QBIT] FILE ADD -> статус={resp.status} тело={body.strip()[:80]}")
            if resp.status == 409:
                return "duplicate"
            if resp.status in [200, 204] and "Fails" not in body:
                return True
            return False

    async def set_category(self, hash_id: str, category: str):
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/setCategory"
        headers = {"Cookie": self.cookie} if qb.cookie else {}
        async with self.session.post(url, data={"hashes": hash_id, "category": category}, headers=headers) as resp:
            log.info(f"[QBIT] SET_CATEGORY {hash_id[:8]}... -> {category} | статус={resp.status}")

    async def resume_torrent(self, hashes: str):
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/start"
        headers = {"Cookie": self.cookie} if self.cookie else {}
        await self.session.post(url, data={"hashes": hashes}, headers=headers)
        log.info(f"[QBIT] RESUME {hashes[:8]}...")

    async def pause_torrent(self, hashes: str):
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/stop"
        headers = {"Cookie": self.cookie} if self.cookie else {}
        await self.session.post(url, data={"hashes": hashes}, headers=headers)
        log.info(f"[QBIT] PAUSE {hashes[:8]}...")

    async def delete_torrent(self, hashes: str, delete_files: bool = False):
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/delete"
        headers = {"Cookie": self.cookie} if self.cookie else {}
        await self.session.post(url, data={"hashes": hashes, "deleteFiles": str(delete_files).lower()}, headers=headers)
        log.info(f"[QBIT] DELETE {hashes[:8]}... files={delete_files}")

    async def pause_all(self):
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/stop"
        headers = {"Cookie": self.cookie} if self.cookie else {}
        await self.session.post(url, data={"hashes": "all"}, headers=headers)

    async def resume_all(self):
        await self.login()
        url = f"{self.base_url}/api/v2/torrents/start"
        headers = {"Cookie": self.cookie} if self.cookie else {}
        await self.session.post(url, data={"hashes": "all"}, headers=headers)

    async def global_info(self):
        await self.login()
        url = f"{self.base_url}/api/v2/transfer/info"
        headers = {"Cookie": self.cookie} if self.cookie else {}
        async with self.session.get(url, headers=headers) as resp:
            return await resp.json()

qb = QBittorrentClient()
