"""Release-drop engine: when does a spot next open reservations, and which drop
covers a given target date. Python port of nextDrop() in index.html and
docs/ios/countdown-engine.md, extended with the booking-window coverage rule.

All math happens on the city's wall clock via zoneinfo so DST never shifts a drop.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterator
from zoneinfo import ZoneInfo

_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)", re.I)
_WD_RE = re.compile(r"sun|mon|tue|wed|thu|fri|sat", re.I)
_WD = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
_DOM_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b", re.I)

DAILY = "daily"
WEEKLY = "weekly"
TWICE_MONTHLY = "twice-monthly"
MONTHLY_KINDS = {"calendar-month", "monthly"}
NONE = "none"


def parse_release_time(text: str | None) -> tuple[int, int] | None:
    """'10:00 AM ET' -> (10, 0); '12:00 AM (Midnight) ET' -> (0, 0); '(Noon)' -> (12, 0)."""
    if not text:
        return None
    if re.search(r"midnight", text, re.I):
        return (0, 0)
    if re.search(r"noon", text, re.I):
        return (12, 0)
    m = _TIME_RE.search(text)
    if not m:
        return None
    h, mi, ap = int(m[1]), int(m[2]), m[3].upper()
    if ap == "PM" and h != 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    return (h, mi)


def normalize_schedule(text: str | None) -> str:
    s = (text or "").strip().lower().replace("calendar month", "calendar-month")
    return s or NONE


def parse_weekday(text: str | None, default: int = 5) -> int:
    m = _WD_RE.search(text or "")
    return _WD[m[0].lower()] if m else default


def parse_days_of_month(text: str | None) -> list[int]:
    days = sorted({int(d) for d in _DOM_RE.findall(text or "") if 1 <= int(d) <= 31})
    return days or [1]


def releases_previous_month(release_day: str | None) -> bool:
    """'1st of previous month' / 'mid-month for following month' => the drop in month M
    opens month M+1. Plain '1st of each month' opens the same month."""
    return bool(re.search(r"previous|following|next month|month ahead", release_day or "", re.I))


def _wall(tz: ZoneInfo, d: date, hm: tuple[int, int]) -> datetime:
    return datetime(d.year, d.month, d.day, hm[0], hm[1], tzinfo=tz)


def _clamp_dom(y: int, m: int, dom: int) -> date:
    return date(y, m, min(dom, calendar.monthrange(y, m)[1]))


def iter_drops(spot: dict[str, Any], tz: ZoneInfo, start: date) -> Iterator[datetime]:
    """Yield release instants whose local date is >= start, in order. Empty for 'none'."""
    sched = normalize_schedule(spot.get("releaseSchedule"))
    hm = parse_release_time(spot.get("releaseTime"))
    if sched == NONE or hm is None:
        return
    if sched == DAILY:
        d = start
        while True:
            yield _wall(tz, d, hm)
            d += timedelta(days=1)
    elif sched == WEEKLY:
        target = parse_weekday(spot.get("releaseDay"))
        d = start + timedelta(days=(target - start.weekday()) % 7)
        while True:
            yield _wall(tz, d, hm)
            d += timedelta(days=7)
    else:  # calendar-month / monthly / twice-monthly
        doms = [1, 15] if sched == TWICE_MONTHLY else parse_days_of_month(spot.get("releaseDay"))
        y, m = start.year, start.month
        while True:
            for dom in doms:
                d = _clamp_dom(y, m, dom)
                if d >= start:
                    yield _wall(tz, d, hm)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def next_drop(spot: dict[str, Any], tz: ZoneInfo, now: datetime) -> datetime | None:
    """First release instant strictly after `now` (same semantics as the web countdown).

    Comparisons go through UTC on purpose: two aware datetimes that share one ZoneInfo
    compare and subtract on their naive wall clocks, which is wrong across a DST change.
    """
    now_utc = now.astimezone(timezone.utc)
    for d in iter_drops(spot, tz, now.astimezone(tz).date() - timedelta(days=1)):
        if d.astimezone(timezone.utc) > now_utc:
            return d
    return None


def drop_for_target(spot: dict[str, Any], tz: ZoneInfo, target: date) -> datetime | None:
    """The release instant at which `target` becomes bookable, or None if unscheduled."""
    sched = normalize_schedule(spot.get("releaseSchedule"))
    hm = parse_release_time(spot.get("releaseTime"))
    if sched == NONE or hm is None:
        return None
    window = int(spot.get("bookingWindowDays") or 0)
    if sched in MONTHLY_KINDS:
        y, m = target.year, target.month
        if releases_previous_month(spot.get("releaseDay")) or not spot.get("releaseDay"):
            y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        dom = parse_days_of_month(spot.get("releaseDay"))[0]
        return _wall(tz, _clamp_dom(y, m, dom), hm)
    # daily / weekly / twice-monthly: the earliest drop whose window reaches the target.
    for d in iter_drops(spot, tz, target - timedelta(days=window)):
        if d.date() > target:
            break
        return d
    return None


def describe(spot: dict[str, Any], tz_name: str, target: date | None = None,
             now: datetime | None = None) -> dict[str, Any]:
    """Tool-shaped summary used by next_drop() in agent/tools."""
    tz = ZoneInfo(tz_name)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    out: dict[str, Any] = {
        "spot_id": spot.get("id"),
        "schedule": normalize_schedule(spot.get("releaseSchedule")),
        "release_time": spot.get("releaseTime") or "",
        "release_day": spot.get("releaseDay") or "",
        "booking_window_days": spot.get("bookingWindowDays"),
        "timezone": tz_name,
        "now_local": now.astimezone(tz).isoformat(timespec="seconds"),
    }
    nd = next_drop(spot, tz, now)
    out["next_drop"] = _instant(nd, tz, now)
    if target:
        cd = drop_for_target(spot, tz, target)
        out["target_date"] = target.isoformat()
        out["drop_for_target"] = _instant(cd, tz, now)
        if cd is not None:
            out["drop_for_target"]["already_released"] = cd.astimezone(timezone.utc) <= now
    if nd is None:
        out["note"] = ("No scheduled release: reservations are not opened on a fixed "
                       "drop. Use the booking link or walk-in guidance instead.")
    return out


def _instant(d: datetime | None, tz: ZoneInfo, now: datetime) -> dict[str, Any] | None:
    if d is None:
        return None
    secs = int((d.astimezone(timezone.utc) - now.astimezone(timezone.utc)).total_seconds())
    local = d.astimezone(tz)
    return {
        "utc": d.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "local": local.isoformat(timespec="seconds"),
        "local_pretty": local.strftime("%a %b %d, %I:%M %p %Z").replace(" 0", " "),
        "seconds_until": secs,
        "countdown": fmt_countdown(secs),
    }


def fmt_countdown(secs: int) -> str:
    if secs <= 0:
        return "LIVE"
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m {s:02d}s"
    return f"{m}m {s:02d}s"
