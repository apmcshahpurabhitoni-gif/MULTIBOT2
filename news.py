"""Small, cache-friendly informational news feed for the dashboard.

News is presentation-only. It never changes strategy, freshness, risk, or trade
execution state. The dashboard uses Google News RSS for India/NSE market headlines
and clearly reports when the external feed is unavailable.
"""
from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from threading import RLock


NEWS_TTL_SECONDS = 300
NEWS_URL = "https://news.google.com/rss/search?"


class NewsService:
    def __init__(self, *, ttl_seconds: int = NEWS_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = RLock()
        self._cached: dict | None = None
        self._cached_at = 0.0

    def _fetch(self) -> dict:
        query = urllib.parse.urlencode(
            {"q": "NSE India OR NIFTY 50 OR Indian stock market", "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        )
        request = urllib.request.Request(
            NEWS_URL + query,
            headers={"User-Agent": "MULTIBOT2/1.0 news dashboard"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            root = ET.fromstring(response.read())

        items = []
        for item in root.findall("./channel/item")[:12]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = (item.findtext("pubDate") or "").strip()
            source = item.findtext("source") or "Google News"
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "url": link,
                    "source": source,
                    "published_at": published,
                }
            )

        return {
            "status": "ONLINE",
            "source": "Google News RSS",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
            "message": f"{len(items)} headlines available" if items else "Feed connected but no headlines returned",
        }

    def get(self, *, force: bool = False) -> dict:
        with self._lock:
            if not force and self._cached is not None and time.monotonic() - self._cached_at < self.ttl_seconds:
                return self._cached
            try:
                result = self._fetch()
            except Exception as exc:
                result = {
                    "status": "OFFLINE",
                    "source": "Google News RSS",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "items": [],
                    "message": f"News feed unavailable: {type(exc).__name__}",
                }
            self._cached = result
            self._cached_at = time.monotonic()
            return result

    def refresh(self) -> dict:
        with self._lock:
            self._cached = None
            self._cached_at = 0.0
        return self.get(force=True)


__all__ = ["NewsService", "NEWS_TTL_SECONDS"]
