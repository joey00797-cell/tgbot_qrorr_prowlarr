import re
import logging
import aiohttp
from config.settings import TMDB_API_KEY

log = logging.getLogger("torrent_bot")

async def get_movie_metadata(query: str, year: str = None):
    try:
        clean_title = query.split('(')[0].split('[')[0].strip()
        sub_titles = [t.strip() for t in re.split(r'[/|]', clean_title) if t.strip()]
        search_query = sub_titles[0] if sub_titles else clean_title
        
        search_url = f"https://api.themoviedb.org/3/search/multi"
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
                        
            return {
                "title": target_item.get("title") or target_item.get("name"),
                "overview": target_item.get("overview", "Нет описания"),
                "release": target_item.get("release_date") or target_item.get("first_air_date", "N/A")
            }
    except Exception as e:
        log.error(f"[TMDB] Ошибка получения метаданных: {e}")
    return None
