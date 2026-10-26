"""Countdown-engine cases from docs/ios/countdown-engine.md, run against agent/drops.py."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from agent import drops

NY = ZoneInfo("America/New_York")


def spot(**kw):
    base = {"id": "x", "releaseSchedule": "daily", "releaseTime": "10:00 AM ET",
            "releaseDay": "", "bookingWindowDays": 30}
    base.update(kw)
    return base


def test_parse_release_time():
    assert drops.parse_release_time("10:00 AM ET") == (10, 0)
    assert drops.parse_release_time("12:00 AM (Midnight) ET") == (0, 0)
    assert drops.parse_release_time("12:00 PM (Noon) ET") == (12, 0)
    assert drops.parse_release_time("9:00 AM") == (9, 0)
    assert drops.parse_release_time("3:00 PM ET") == (15, 0)
    assert drops.parse_release_time("N/A") is None
    assert drops.parse_release_time("") is None


def test_daily_one_second_before_and_after():
    before = datetime(2026, 10, 27, 9, 59, 59, tzinfo=NY)
    nd = drops.next_drop(spot(), NY, before)
    assert (nd - before).total_seconds() == 1
    after = datetime(2026, 10, 27, 10, 0, 1, tzinfo=NY)
    nd = drops.next_drop(spot(), NY, after)
    assert nd == datetime(2026, 10, 28, 10, 0, tzinfo=NY)


def test_weekly_saturday_midnight():
    s = spot(releaseSchedule="weekly", releaseTime="12:00 AM (Midnight) ET", releaseDay="Saturday midnight")
    now = datetime(2026, 10, 31, 0, 0, 30, tzinfo=NY)  # a Saturday
    nd = drops.next_drop(s, NY, now)
    assert nd == datetime(2026, 11, 7, 0, 0, tzinfo=NY)
    assert (nd - now) == timedelta(days=7, seconds=-30)


def test_calendar_month_rolls_over_short_months():
    s = spot(releaseSchedule="calendar-month", releaseTime="9:00 AM ET", releaseDay="1st of previous month")
    now = datetime(2026, 10, 31, 23, 59, tzinfo=NY)
    assert drops.next_drop(s, NY, now) == datetime(2026, 11, 1, 9, 0, tzinfo=NY)
    now = datetime(2026, 11, 30, 23, 59, tzinfo=NY)
    assert drops.next_drop(s, NY, now) == datetime(2026, 12, 1, 9, 0, tzinfo=NY)


def test_dst_week_keeps_wall_clock():
    # US fall-back is Sun 1 Nov 2026 at 2 AM. A 10 AM daily drop stays 10 AM local
    # across it: Sat noon -> Sun 10 AM is 22 h on the wall clock, 23 h of real time.
    now = datetime(2026, 10, 31, 12, 0, tzinfo=NY)
    nd = drops.next_drop(spot(), NY, now)
    assert nd.hour == 10 and nd.date() == date(2026, 11, 1)
    # Same-tz subtraction would say 22 h; the engine's UTC math says 23 h.
    assert (nd.astimezone(timezone.utc) - now.astimezone(timezone.utc)).total_seconds() == 23 * 3600
    assert drops.describe(spot(), "America/New_York", now=now)["next_drop"]["seconds_until"] == 23 * 3600


def test_none_schedule_has_no_drop():
    s = spot(releaseSchedule="none", releaseTime="")
    assert drops.next_drop(s, ZoneInfo("Europe/Madrid"), datetime(2026, 10, 27, tzinfo=NY)) is None
    assert drops.drop_for_target(s, ZoneInfo("Europe/Madrid"), date(2026, 11, 7)) is None


def test_daily_window_coverage():
    # Carbone: daily 10 AM, 30-day window. Sat 7 Nov is opened by the drop on 8 Oct.
    cd = drops.drop_for_target(spot(), NY, date(2026, 11, 7))
    assert cd == datetime(2026, 10, 8, 10, 0, tzinfo=NY)
    now = datetime(2026, 10, 27, 12, 0, tzinfo=NY)
    d = drops.describe(spot(), "America/New_York", date(2026, 11, 7), now)
    assert d["drop_for_target"]["already_released"] is True
    # A date beyond the window: 30 Nov opens on 31 Oct at 10 AM, still ahead of "now".
    d = drops.describe(spot(), "America/New_York", date(2026, 11, 30), now)
    assert d["drop_for_target"]["local"].startswith("2026-10-31T10:00")
    assert d["drop_for_target"]["already_released"] is False


def test_weekly_window_coverage():
    s = spot(releaseSchedule="weekly", releaseTime="9:00 AM ET", releaseDay="Thursday", bookingWindowDays=14)
    # Target Sat 14 Nov: earliest Thursday drop on/after 31 Oct is Thu 5 Nov.
    assert drops.drop_for_target(s, NY, date(2026, 11, 14)) == datetime(2026, 11, 5, 9, 0, tzinfo=NY)


def test_monthly_previous_month_rule():
    s = spot(releaseSchedule="calendar-month", releaseTime="9:00 AM ET", releaseDay="1st of previous month")
    assert drops.drop_for_target(s, NY, date(2026, 11, 20)) == datetime(2026, 10, 1, 9, 0, tzinfo=NY)
    s = spot(releaseSchedule="monthly", releaseTime="12:00 PM (Noon) ET", releaseDay="21st of previous month")
    assert drops.drop_for_target(s, NY, date(2027, 1, 5)) == datetime(2026, 12, 21, 12, 0, tzinfo=NY)


def test_twice_monthly():
    s = spot(releaseSchedule="twice-monthly", releaseTime="10:00 AM ET", releaseDay="1st & 15th", bookingWindowDays=30)
    now = datetime(2026, 10, 27, 12, 0, tzinfo=NY)
    assert drops.next_drop(s, NY, now) == datetime(2026, 11, 1, 10, 0, tzinfo=NY)


def test_fmt_countdown():
    assert drops.fmt_countdown(0) == "LIVE"
    assert drops.fmt_countdown(59) == "0m 59s"
    assert drops.fmt_countdown(3661) == "1h 1m 01s"
    assert drops.fmt_countdown(2 * 86400 + 3 * 3600 + 4 * 60) == "2d 3h 4m"
