# 🤖 Torrent Bot v2

Telegram-бот для поиска и управления торрентами с полной интеграцией в медиастек.

## ⚙️ Стек

- **aiogram 3** — Telegram Bot framework
- **qBittorrent** — торрент-клиент
- **Prowlarr** — агрегатор индексеров
- **Radarr** — управление фильмами
- **Sonarr** — управление сериалами
- **Jellyfin** — медиасервер
- **TMDB** — метаданные фильмов и сериалов
- **SQLite (aiosqlite)** — хранилище пользователей, загрузок, истории, вотчлиста

## ✨ Возможности

- 🔍 Поиск торрентов через Prowlarr с фильтрацией по сезону и озвучке
- 📥 Добавление на паузу с выбором категории (фильм/сериал/прочее) и уведомлений
- 🎬 Автоматическое добавление в Radarr/Sonarr после подтверждения скачивания
- 📊 Дашборд статуса закачек с пагинацией
- 🕐 История поиска с повтором запроса
- 🔔 Уведомления о завершении закачки (только мне / всем)
- 🔄 Вотчлист — слежение за обновлениями раздач
- 👥 Система доступа пользователей (активация/блок через админку)
- 🔧 Панель настроек для админа (статус дисков, очистка кеша, docker prune, перезапуск)
- 🛰 Watchdog — мониторинг завершения закачек в фоне

## 🚀 Установка

```bash
git clone https://github.com/joey00797-cell/tgbot_qrorr_prowlarr.git
cd tgbot_qrorr_prowlarr
cp .env.example .env
```

Заполни `.env` своими значениями, затем:

```bash
docker compose build --build-arg CACHE_BUST=$(date +%s) torrent-bot-v2
docker compose up -d torrent-bot-v2
```

## 🔧 Переменные окружения

| Переменная | Описание |
|---|---|
| `TELEGRAM_TOKEN` | Токен бота от @BotFather |
| `ADMIN_ID` | Telegram ID администратора |
| `ADMIN_USERNAME` | Username администратора |
| `QBIT_HOST` | IP адрес qBittorrent |
| `QBIT_PORT` | Порт qBittorrent (default: 8080) |
| `QBIT_USER` | Логин qBittorrent |
| `QBIT_PASSWORD` | Пароль qBittorrent |
| `PROWLARR_BASE_URL` | URL Prowlarr (http://ip:9696) |
| `PROWLARR_API_KEY` | API ключ Prowlarr |
| `TMDB_API_KEY` | API ключ TMDB |
| `RADARR_URL` | URL Radarr (http://ip:7878) |
| `RADARR_KEY` | API ключ Radarr |
| `SONARR_URL` | URL Sonarr (http://ip:8989) |
| `SONARR_KEY` | API ключ Sonarr |
| `QBIT_CAT_MOVIE` | Категория фильмов (default: radarr) |
| `QBIT_CAT_TV` | Категория сериалов (default: tv-sonarr) |
| `DEBUG_MODE` | Режим отладки (default: False) |
| `TZ` | Timezone (default: Europe/Kiev) |

## 📁 Структура проекта

```
app_v2/
├── entrypoint.py
├── bootstrap.py           — инициализация, health checks при старте
├── config/settings.py     — переменные окружения
├── routers/
│   ├── menu.py            — /start, главное меню
│   ├── admin.py           — управление пользователями
│   ├── torrents.py        — дашборд закачек
│   ├── search.py          — поиск, карточка, выбор категории
│   ├── history.py         — история поиска
│   ├── settings.py        — панель настроек для админа
│   └── talker.py          — пинг, аптайм
├── services/
│   ├── qbittorrent.py     — HTTP-клиент qBit
│   ├── watchdog.py        — мониторинг завершения закачек
│   ├── prowlarr.py        — поиск раздач
│   ├── metadata.py        — TMDB метаданные
│   └── arrs.py            — интеграция с Radarr и Sonarr
├── storage/
│   ├── database.py        — SQLite пул (aiosqlite)
│   ├── users.py
│   ├── downloads.py
│   ├── history.py
│   └── watchlist.py
└── utils/
    ├── logger.py
    └── formatters.py
```

## 🔄 Флоу скачивания

1. Пользователь ищет → выбирает раздачу
2. Торрент добавляется в qBit **на паузе**
3. Пользователь выбирает категорию (фильм/сериал) и уведомления
4. После подтверждения:
   - qBit: устанавливается категория + торрент запускается
   - Radarr/Sonarr: фильм/сериал добавляется по TMDB ID автоматически
5. После скачивания Radarr/Sonarr импортируют файл → Jellyfin подхватывает

## 📡 Status Server (опционально)

Для отображения статуса дисков в панели настроек бота нужен простой HTTP сервер
на машине с arr-стаком (порт 9999). Пример скрипта в `scripts/status_server.py`.
Укажи его URL в `config/settings.py` → `STATUS_SERVER_URL`.
