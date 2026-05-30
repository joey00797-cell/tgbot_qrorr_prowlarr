import re
import aiohttp
from config.settings import PROWLARR_BASE_URL, PROWLARR_API_KEY

# Паттерны сезона в запросе пользователя
_SEASON_PATTERNS = [
    r'сезон\s*(\d+)',
    r'(\d+)\s*сезон',
    r'season\s*(\d+)',
    r'(\d+)\s*season',
    r'\bs(\d{1,2})\b',
]

# Алиасы озвучек: что пишет пользователь -> что ищем в названии торрента
_VOICE_ALIASES = {
    'lostfilm':       'LostFilm',
    'лостфильм':      'LostFilm',
    'лост':           'LostFilm',
    'alexfilm':       'AlexFilm',
    'алекс':          'AlexFilm',
    'алексфильм':     'AlexFilm',
    'tvshows':        'TVShows',
    'твшоус':         'TVShows',
    'твшows':         'TVShows',
    'hdrezka':        'HDRezka',
    'резка':          'HDRezka',
    'хдрезка':        'HDRezka',
    'kubik':          'Kubik',
    'кубик':          'Kubik',
    'rhs':            'Red Head Sound',
    'redheadsound':   'Red Head Sound',
    'red head sound': 'Red Head Sound',
    'краснаяголова':  'Red Head Sound',
    'newstudio':      'NewStudio',
    'нью студио':     'NewStudio',
    'ньюстудио':      'NewStudio',
    'jaskier':        'Jaskier',
    'яскер':          'Jaskier',
    'coldfilm':       'ColdFilm',
    'колдфильм':      'ColdFilm',
    'колд':           'ColdFilm',
    'leproduction':   'LE-Production',
    'le-production':  'LE-Production',
    'le production':  'LE-Production',
    'dragonmoney':    'Dragon Money',
    'dragon money':   'Dragon Money',
    'дракон':         'Dragon Money',
    'kerotv':         'KerobTV',
    'кероТВ':         'KerobTV',
    'rudub':          'RuDub',
    'рудаб':          'RuDub',
    'goblin':         'Гоблин',
    'гоблин':         'Гоблин',
}

def extract_season(query: str):
    """Возвращает (номер_сезона_int, очищенный_запрос) или (None, query)."""
    for pat in _SEASON_PATTERNS:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            season = int(m.group(1))
            clean = re.sub(pat, '', query, flags=re.IGNORECASE).strip()
            clean = re.sub(r'\s{2,}', ' ', clean).strip()
            return season, clean
    return None, query

def extract_voice(query: str):
    """Возвращает (название_студии, очищенный_запрос) или (None, query)."""
    q_lower = query.lower()
    # Сначала проверяем многословные алиасы (длиннее сначала)
    for alias in sorted(_VOICE_ALIASES.keys(), key=len, reverse=True):
        if alias in q_lower:
            studio = _VOICE_ALIASES[alias]
            clean = re.sub(re.escape(alias), '', q_lower, flags=re.IGNORECASE)
            # Восстанавливаем оригинальный регистр для остатка
            clean = re.sub(r'\s{2,}', ' ', clean).strip()
            return studio, clean
    return None, query

def _season_in_title(title: str, season: int) -> bool:
    """Проверяет что в названии есть нужный сезон."""
    t = title.lower()
    season_str = str(season)
    season_padded = f"{season:02d}"
    patterns = [
        rf's{season_padded}',
        rf's{season_str}\b',
        rf's{season_padded}e\d',
        rf'сезон\s*{season_str}\b',
        rf'season\s*{season_str}\b',
        rf'\({season_str}\s*сезон\)',
        rf'[\s\(]{season_str}\s*сезон',
    ]
    return any(re.search(p, t) for p in patterns)

def _voice_in_title(title: str, studio: str) -> bool:
    """Проверяет что в названии есть нужная студия озвучки."""
    return studio.lower() in title.lower()

def _matches_query(title: str, query: str) -> bool:
    """Все слова запроса должны присутствовать в названии."""
    title_lower = title.lower()
    words = query.lower().split()
    return all(w in title_lower for w in words)

async def search(query: str):
    season, q1 = extract_season(query)
    voice, clean_query = extract_voice(q1)

    # Строим запрос для Prowlarr
    prowlarr_query = clean_query
    if season is not None:
        prowlarr_query = f"{clean_query} S{season:02d}"

    url = f"{PROWLARR_BASE_URL}/api/v1/search"
    headers = {"X-Api-Key": PROWLARR_API_KEY}
    params = {"query": prowlarr_query}
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                body = await response.text()
                raise Exception(f"Prowlarr error {response.status}: {body}")
            data = await response.json()

    # Фильтр по словам
    filtered = [item for item in data if _matches_query(item.get("title", ""), clean_query)]

    # Фильтр по сезону
    if season is not None:
        filtered_season = [item for item in filtered if _season_in_title(item.get("title", ""), season)]
        filtered = filtered_season if filtered_season else filtered

    # Фильтр по озвучке
    if voice is not None:
        filtered_voice = [item for item in filtered if _voice_in_title(item.get("title", ""), voice)]
        filtered = filtered_voice if filtered_voice else filtered

    return filtered if filtered else data
