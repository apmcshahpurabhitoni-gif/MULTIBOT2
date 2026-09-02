"""Forex Factory economic-calendar service for the Mavis dashboard.

The calendar is informational only. It never changes strategy, freshness,
risk, execution, Telegram dispatch, or the locked trading rules.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from threading import RLock
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
FF_TZ = ZoneInfo("America/New_York")
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
NEXT_WEEK_URL = "https://nfs.faireconomy.media/ff_calendar_nextweek.json"
FOREX_FACTORY_CALENDAR = "https://www.forexfactory.com/calendar"
CACHE_TTL_SECONDS = 3600
IMPACTS = ("High", "Medium", "Low", "Holiday")


class CalendarService:
    """Rate-conscious reader for the public Forex Factory weekly JSON feed."""

    def __init__(self, *, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = RLock()
        self._cache: dict[str, tuple[list[dict], float]] = {}
        self._last_error: str | None = None

    @staticmethod
    def _week_start(day: date) -> date:
        return day - timedelta(days=day.weekday())

    def _feed_url(self, target: date) -> tuple[str, str] | None:
        current = datetime.now(IST).date()
        current_week = self._week_start(current)
        target_week = self._week_start(target)
        if target_week == current_week:
            return "thisweek", CALENDAR_URL
        if target_week == current_week + timedelta(days=7):
            return "nextweek", NEXT_WEEK_URL
        return None

    def _fetch_feed(self, feed_key: str, url: str, *, force: bool = False) -> list[dict]:
        cached = self._cache.get(feed_key)
        if not force and cached and time.monotonic() - cached[1] < self.ttl_seconds:
            return cached[0]

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mavis-MULTIBOT2/1.1 economic-calendar",
                "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("Forex Factory calendar feed returned an unexpected payload")

        events: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            raw_date = str(item.get("date") or "").strip()
            if not raw_date:
                continue
            try:
                dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=FF_TZ)
            local_dt = dt.astimezone(IST)
            impact = str(item.get("impact") or "Low").strip().title()
            if impact not in IMPACTS:
                impact = "Low"
            country = str(item.get("country") or "").strip().upper()
            events.append(
                {
                    "id": f"{raw_date}|{country}|{item.get('title', '')}",
                    "date": local_dt.date().isoformat(),
                    "time": local_dt.strftime("%H:%M"),
                    "datetime": local_dt.isoformat(),
                    "currency": country,
                    "impact": impact,
                    "title": str(item.get("title") or "Economic event").strip(),
                    "actual": str(item.get("actual") or "").strip(),
                    "forecast": str(item.get("forecast") or "").strip(),
                    "previous": str(item.get("previous") or "").strip(),
                    "source": "Forex Factory",
                    "url": FOREX_FACTORY_CALENDAR,
                }
            )

        events.sort(key=lambda item: item["datetime"])
        self._cache[feed_key] = (events, time.monotonic())
        self._last_error = None
        return events

    def get(
        self,
        *,
        target_date: str | None = None,
        impacts: set[str] | None = None,
        force: bool = False,
    ) -> dict:
        target = datetime.now(IST).date() if not target_date else date.fromisoformat(target_date)
        feed = self._feed_url(target)
        if feed is None:
            return {
                "status": "OUT_OF_RANGE",
                "source": "Forex Factory",
                "date": target.isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "items": [],
                "counts": {impact.lower(): 0 for impact in IMPACTS},
                "message": "Forex Factory provides a rolling weekly feed; choose a date in the current or next calendar week.",
                "calendar_url": FOREX_FACTORY_CALENDAR,
            }

        feed_key, feed_url = feed
        try:
            events = self._fetch_feed(feed_key, feed_url, force=force)
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            cached = self._cache.get(feed_key)
            if cached:
                events = cached[0]
                status = "STALE_CACHE"
            else:
                return {
                    "status": "OFFLINE",
                    "source": "Forex Factory",
                    "date": target.isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "items": [],
                    "counts": {impact.lower(): 0 for impact in IMPACTS},
                    "message": f"Forex Factory feed unavailable: {self._last_error}",
                    "calendar_url": FOREX_FACTORY_CALENDAR,
                }
        else:
            status = "ONLINE"

        selected = [event for event in events if event["date"] == target.isoformat()]
        selected_impacts = {item.title() for item in (impacts or set(IMPACTS))}
        if "All" not in selected_impacts:
            selected = [event for event in selected if event["impact"] in selected_impacts]
        counts = {impact.lower(): sum(event["impact"] == impact for event in selected) for impact in IMPACTS}
        return {
            "status": status,
            "source": "Forex Factory",
            "date": target.isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "items": selected,
            "counts": counts,
            "message": f"{len(selected)} events for {target.strftime('%d %b %Y')}",
            "calendar_url": f"{FOREX_FACTORY_CALENDAR}?day={target.strftime('%b').lower()}{target.day}.{target.year}",
        }

    def refresh(self, *, target_date: str | None = None, impacts: set[str] | None = None) -> dict:
        with self._lock:
            self._cache.clear()
            return self.get(target_date=target_date, impacts=impacts, force=True)


NewsService = CalendarService

__all__ = ["CalendarService", "NewsService", "CACHE_TTL_SECONDS"]
