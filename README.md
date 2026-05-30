# 🤖 Torrent Bot v2

Telegram-бот для управления торрентами через qBittorrent и поиска раздач через Prowlarr.

## ⚙️ Стек

- **aiogram 3** — Telegram Bot framework
- **qBittorrent** — торрент-клиент
- **Prowlarr** — агрегатор индексеров
- **TMDB** — метаданные фильмов и сериалов

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
| `QBIT_HOST` | IP адрес qBittorrent |
| `QBIT_PORT` | Порт qBittorrent (default: 8080) |
| `QBIT_USER` | Логин qBittorrent |
| `QBIT_PASSWORD` | Пароль qBittorrent |
| `PROWLARR_BASE_URL` | URL Prowlarr (http://ip:9696) |
| `PROWLARR_API_KEY` | API ключ Prowlarr |
| `TMDB_API_KEY` | API ключ TMDB |
| `QBIT_CAT_MOVIE` | Категория фильмов (default: radarr) |
| `QBIT_CAT_TV` | Категория сериалов (default: tv-sonarr) |
| `TZ` | Timezone (default: Europe/Kiev) |

## ✨ Возможности

- 🔍 Поиск торрентов через Prowlarr с фильтрацией по сезону и озвучке
- 📥 Добавление на паузу с выбором категории и уведомлений
- 📊 Дашборд статуса закачек
- 🕐 История поиска
- 🔔 Уведомления о завершении закачки
- 👥 Система доступа пользователей
