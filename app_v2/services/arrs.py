import logging
import aiohttp
import config as _config

log = logging.getLogger("torrent_bot")

RADARR_URL = _config.RADARR_URL
RADARR_KEY = _config.RADARR_KEY
SONARR_URL = _config.SONARR_URL
SONARR_KEY = _config.SONARR_KEY

RADARR_QUALITY_PROFILE = 4   # HD-1080p
RADARR_ROOT_FOLDER     = "/media/movies"
SONARR_QUALITY_PROFILE = 1
SONARR_ROOT_FOLDER     = "/media/series"

async def _get(url, key, path):
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{url}{path}", headers={"X-Api-Key": key}) as r:
            return await r.json()

async def _post(url, key, path, data):
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{url}{path}", json=data, headers={"X-Api-Key": key}) as r:
            return r.status, await r.json()

async def add_to_radarr(tmdb_id: int) -> dict:
    try:
        movie = await _get(RADARR_URL, RADARR_KEY, f"/api/v3/movie/lookup/tmdb?tmdbId={tmdb_id}")
        status, result = await _post(RADARR_URL, RADARR_KEY, "/api/v3/movie", {
            "tmdbId":           movie["tmdbId"],
            "title":            movie["title"],
            "year":             movie["year"],
            "qualityProfileId": RADARR_QUALITY_PROFILE,
            "rootFolderPath":   RADARR_ROOT_FOLDER,
            "monitored":        True,
            "addOptions":       {"searchForMovie": False},
        })
        if status == 201:
            log.info(f"[RADARR] Added: {movie['title']} ({movie['year']}) id={result['id']}")
            return {"ok": True, "id": result["id"], "title": movie["title"]}
        elif status == 400 and "already" in str(result).lower():
            log.info(f"[RADARR] Already exists: {movie['title']}")
            return {"ok": True, "exists": True, "title": movie["title"]}
        else:
            log.error(f"[RADARR] Error {status}: {result}")
            return {"ok": False, "error": str(result)}
    except Exception as e:
        log.error(f"[RADARR] Exception: {e}")
        return {"ok": False, "error": str(e)}

async def add_to_sonarr(tmdb_id: int) -> dict:
    try:
        results = await _get(SONARR_URL, SONARR_KEY, f"/api/v3/series/lookup?term=tmdb:{tmdb_id}")
        if not results:
            return {"ok": False, "error": "Сериал не найден в Sonarr"}
        series = results[0]
        status, result = await _post(SONARR_URL, SONARR_KEY, "/api/v3/series", {
            "tvdbId":           series["tvdbId"],
            "title":            series["title"],
            "year":             series.get("year", 0),
            "qualityProfileId": SONARR_QUALITY_PROFILE,
            "rootFolderPath":   SONARR_ROOT_FOLDER,
            "monitored":        True,
            "seasonFolder":     True,
            "addOptions":       {"searchForMissingEpisodes": False},
            "seasons":          series.get("seasons", []),
        })
        if status == 201:
            log.info(f"[SONARR] Added: {series['title']} id={result['id']}")
            return {"ok": True, "id": result["id"], "title": series["title"]}
        elif status == 400 and "already" in str(result).lower():
            log.info(f"[SONARR] Already exists: {series['title']}")
            return {"ok": True, "exists": True, "title": series["title"]}
        else:
            log.error(f"[SONARR] Error {status}: {result}")
            return {"ok": False, "error": str(result)}
    except Exception as e:
        log.error(f"[SONARR] Exception: {e}")
        return {"ok": False, "error": str(e)}
