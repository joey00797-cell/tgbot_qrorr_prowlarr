import re
import logging
import aiohttp
from config.settings import TMDB_API_KEY

log = logging.getLogger("torrent_bot")

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

TMDB_GENRES = {
    28: "Боевик", 12: "Приключения", 16: "Мультфильм", 35: "Комедия",
    80: "Криминал", 99: "Документальный", 18: "Драма", 10751: "Семейный",
    14: "Фэнтези", 36: "История", 27: "Ужасы", 10402: "Музыка",
    9648: "Мистика", 10749: "Мелодрама", 878: "Фантастика", 10770: "Телефильм",
    53: "Триллер", 10752: "Военный", 37: "Вестерн",
    # сериалы
    10759: "Боевик/Приключения", 10762: "Детский", 10763: "Новости",
    10764: "Реалити", 10765: "Фантастика/Фэнтези", 10766: "Мыльная опера",
    10767: "Ток-шоу", 10768: "Военный/Политика",
}

async def get_movie_metadata(query: str, year: str = None):
    try:
        clean_title = query.split('(')[0].split('[')[0].strip()
        sub_titles = [t.strip() for t in re.split(r'[/|]', clean_title) if t.strip()]
        search_query = sub_titles[0] if sub_titles else clean_title

        search_url = "https://api.themoviedb.org/3/search/multi"
        params = {
            "api_key": TMDB_API_KEY,
            "query": search_query,
            "language": "ru-RU"
        }
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(search_url, params=params) as response:
                if response.status != 200:
                    return None
                data = await response.json()

        if data.get('results'):
            items = data['results']
            target_item = items[0]

            if len(sub_titles) > 1:
                eng_title = sub_titles[1].lower()
                for item in items:
                    orig_name = (item.get("original_title") or item.get("original_name") or "").lower()
                    if eng_title in orig_name or orig_name in eng_title:
                        target_item = item
                        break
            elif year:
                for item in items:
                    rel_date = item.get("release_date") or item.get("first_air_date", "")
                    if year in rel_date:
                        target_item = item
                        break

            poster_path = target_item.get("poster_path")
            poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

            genre_ids = target_item.get("genre_ids", [])
            genres = ", ".join(TMDB_GENRES[g] for g in genre_ids if g in TMDB_GENRES) or None

            return {
                "title": target_item.get("title") or target_item.get("name"),
                "overview": target_item.get("overview", "Нет описания"),
                "release": target_item.get("release_date") or target_item.get("first_air_date", "N/A"),
                "poster_url": poster_url,
                "genres": genres,
                "tmdb_id": target_item.get("id"),
            }
    except Exception as e:
        log.error(f"[TMDB] Ошибка получения метаданных: {e}")
    return None
