# -*- coding: utf-8 -*-
import re
import aiosqlite
from difflib import SequenceMatcher
from storage.database import get_db

_JUNK = {
    'selezen','jaskier','sofcj','nnmclub','rutracker','lostfilm','novafilm',
    'coldfilm','amzn','netflix','web','cut','extended','rip','club',
}

def _normalize(title: str) -> str:
    t = title.lower()
    t = re.sub(r'\b(s\d{1,2}e\d{1,2}[-e\d]*|s\d{1,2}|season\s*\d+|e\d{1,2})\b', '', t)
    t = re.sub(r'\b(web-?dl|web-?rip|bdrip|blu-?ray|hdtv|dvdrip|dlrip|avc|xvid|x264|x265|hevc|hdr|sdr|uhd|dcp|dcprip)\b', '', t)
    t = re.sub(r'\b(2160p|1080p|720p|480p|4k)\b', '', t)
    t = re.sub(r'\b(of\s*\d+|\d{4}|\d+)\b', '', t)
    t = re.sub(r'\b(mkv|avi|mp4|mov)\b', '', t)
    words = re.split(r'[.\-_/\[\](),!\s]+', t)
    words = [w for w in words if w and w not in _JUNK and len(w) > 1]
    return ' '.join(words).strip()

def _extract_season(title: str):
    m = re.search(r's(\d{1,2})|season\s*(\d+)', title.lower())
    if m:
        return int(m.group(1) or m.group(2))
    return None

def _similarity(a: str, b: str) -> int:
    sa, sb = _extract_season(a), _extract_season(b)
    if sa is not None and sb is not None and sa != sb:
        return 0
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0
    if na in nb or nb in na:
        return round(min(len(na), len(nb)) / max(len(na), len(nb)) * 100)
    return round(SequenceMatcher(None, na, nb).ratio() * 100)

async def save_download(hash_id: str, uid: int, title: str, notify: str = "me", tmdb_title: str = ""):
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO downloads (hash_id, uid, title, tmdb_title, notify) VALUES (?, ?, ?, ?, ?)",
            (hash_id.lower(), uid, title, tmdb_title, notify)
        )
        await db.commit()

async def get_download(hash_id: str):
    async with get_db() as db:
        async with db.execute("SELECT * FROM downloads WHERE hash_id = ?", (hash_id.lower(),)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def remove_download(hash_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM downloads WHERE hash_id = ?", (hash_id.lower(),))
        await db.commit()

async def find_similar_downloads(title: str, threshold: int = 65) -> list:
    async with get_db() as db:
        async with db.execute("SELECT hash_id, uid, title, tmdb_title FROM downloads") as cursor:
            rows = await cursor.fetchall()
    results = []
    for row in rows:
        if not row["title"]:
            continue
        score = max(
            _similarity(title, row["title"]),
            _similarity(title, row["tmdb_title"] or "") if row["tmdb_title"] else 0
        )
        if score >= threshold:
            results.append({
                "hash_id": row["hash_id"],
                "uid": row["uid"],
                "title": row["title"],
                "tmdb_title": row["tmdb_title"] or "",
                "similarity": score,
            })
    return sorted(results, key=lambda x: x["similarity"], reverse=True)
