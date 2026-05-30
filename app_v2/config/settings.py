import os

# Telegram
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

# Admin
ADMIN_ID = int(os.environ["ADMIN_ID"])
ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]

# Debug
DEBUG_MODE = os.environ.get("DEBUG_MODE", "False").lower() == "true"

# qBittorrent
QBIT_HOST = os.environ["QBIT_HOST"]
QBIT_PORT = int(os.environ.get("QBIT_PORT", 8080))
QBIT_USER = os.environ["QBIT_USER"]
QBIT_PASSWORD = os.environ["QBIT_PASSWORD"]

# Prowlarr
PROWLARR_BASE_URL = os.environ["PROWLARR_BASE_URL"]
PROWLARR_API_KEY = os.environ["PROWLARR_API_KEY"]

# TMDB
TMDB_API_KEY = os.environ["TMDB_API_KEY"]

# Storage
BASE_DIR = "/app/app_v2"
STORAGE_DIR = f"{BASE_DIR}/storage"
USERS_DB = f"{STORAGE_DIR}/users.json"
CACHE_DB = f"{STORAGE_DIR}/cache.json"
DB_FILE = USERS_DB

# qBittorrent категории
QBIT_CAT_MOVIE = os.environ.get("QBIT_CAT_MOVIE", "radarr")
QBIT_CAT_TV = os.environ.get("QBIT_CAT_TV", "tv-sonarr")
