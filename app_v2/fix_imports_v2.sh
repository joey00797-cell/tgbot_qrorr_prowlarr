#!/bin/bash

FILES=$(grep -rl "from app_v2" /opt/torrent-bot/app_v2)

for f in $FILES; do
  sed -i 's/from services/from services/g' "$f"
  sed -i 's/import services/import services/g' "$f"
done
