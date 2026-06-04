import sys

path = '/opt/torrent-bot/app_v2/bootstrap.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """async def on_startup(bot: Bot):
    asyncio.create_task(torrent_watchdog_loop(bot))
    log.info("✅ Watchdog запущен!")"""

new_block = """async def on_startup(bot: Bot):
    try:
        from storage.database import init_db
        await init_db()
python3 << 'EOF'
path = '/opt/torrent-bot/app_v2/bootstrap.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """async def on_startup(bot: Bot):
    asyncio.create_task(torrent_watchdog_loop(bot))
    log.info("✅ Watchdog запущен!")"""
new = """async def on_startup(bot: Bot):
    try:
        from storage.database import init_db
        await init_db()
        log.info("✅ База данных SQLite ус�    except Exception as e:�ешно инициализирована!")
    except Exception as e:
        log.error( Ошибка инициализации базы данных: {e}")f"
    asyncio.create_task(torrent_watchdog_loop(bot))
    log.info("✅ Watchdog запущен!")"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK")
else:
    print("NOT FOUND")
