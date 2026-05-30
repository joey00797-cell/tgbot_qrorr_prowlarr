#!/bin/bash

files=$(grep -rl "from services" /opt/torrent-bot/app_v2)

for f in $files; do
  sed -i 's/from services\.auth/from services.auth/g' "$f"
  sed -i 's/from services\.qbittorrent/from services.qbittorrent/g' "$f"
  sed -i 's/from services import prowlarr/from services import prowlarr/g' "$f"
done
