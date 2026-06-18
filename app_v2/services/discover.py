import logging
import random
import aiohttp
import config as _config

log = logging.getLogger("torrent_bot")

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"

GENRES_MOVIE = {
    28: "Боевик", 12: "Приключения", 16: "Мультфильм", 35: "Комедия",
    80: "Криминал", 99: "Документальный", 18: "Драма", 10751: "Семейный",
    14: "Фэнтези", 36: "История", 27: "Ужасы", 10402: "Музыка",
    9648: "Детектив", 10749: "Мелодрама", 878: "Фантастика",
    10770: "ТВ-фильм", 53: "Триллер", 10752: "Военный", 37: "Вестерн"
}

GENRES_TV = {
    10759: "Боевик/Приключения", 16: "Мультфильм", 35: "Комедия",
    80: "Криминал", 99: "Документальный", 18: "Драма", 10751: "Семейный",
    10762: "Детский", 9648: "Детектив", 10763: "Новости", 10764: "Реалити",
    878: "Фантастика", 10765: "Фантастика/Фэнтези", 10766: "Мыльная опера",
    10767: "Ток-шоу", 10768: "Война/Политика", 37: "Вестерн"
}

async def get_genres(media_type: str = "movie") -> dict:
    return GENRES_MOVIE if media_type != "tv" else GENRES_TV

async def discover(media_type: str = "movie", genre_ids: list = None,
                   min_year: int = 2000, min_rating: float = 6.5,
                   random_pick: bool = True) -> dict | None:
    params = {
        "api_key": _config.TMDB_API_KEY,
        "language": "ru-RU",
        "sort_by": "popularity.desc",
        "vote_count.gte": 500,
        "vote_average.gte": min_rating,
        "page": 1,
    }

    if media_type == "movie":
        params["primary_release_date.gte"] = f"{min_year}-01-01"
    else:
        params["first_air_date.gte"] = f"{min_year}-01-01"

    if genre_ids:
        params["with_genres"] = ",".join(str(g) for g in genre_ids)

    endpoint = f"{TMDB_BASE}/discover/{media_type}"

    try:
        async with aiohttp.ClientSession() as s:
            # сначала узнаём сколько страниц
            async with s.get(endpoint, params=params) as r:
                data = await r.json()

            total_pages = min(data.get("total_pages", 1), 20)
            results = data.get("results", [])

            if random_pick and total_pages > 1:
                params["page"] = random.randint(1, total_pages)
                async with s.get(endpoint, params=params) as r:
                    data = await r.json()
                results = data.get("results", [])

            if not results:
                return None

            item = random.choice(results)
            poster = f"{POSTER_BASE}{item['poster_path']}" if item.get("poster_path") else None
            title = item.get("title") or item.get("name", "Без названия")
            overview = item.get("overview", "Нет описания")
            if len(overview) > 600:
                overview = overview[:600] + "..."
            release = (item.get("release_date") or item.get("first_air_date", ""))[:4]
            rating = item.get("vote_average", 0)
            tmdb_id = item.get("id")
            genre_names = []
            genres_map = GENRES_MOVIE if media_type == "movie" else GENRES_TV
            for gid in item.get("genre_ids", [])[:3]:
                if gid in genres_map:
                    genre_names.append(genres_map[gid])

            original_title = item.get("original_title") or item.get("original_name", title)
            search_query = f"{original_title} {release}" if release else original_title

            return {
                "tmdb_id": tmdb_id,
                "title": title,
                "original_title": original_title,
                "search_query": search_query,
                "overview": overview,
                "release": release,
                "rating": rating,
                "poster": poster,
                "genres": ", ".join(genre_names),
                "media_type": media_type,
            }
    except Exception as e:
        log.error(f"[DISCOVER] Error: {e}")
        return None
