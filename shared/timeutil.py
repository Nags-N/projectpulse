"""UTC storage and Asia/Kolkata display helpers."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
DISPLAY_TZ_NAME = "Asia/Kolkata"
DISPLAY_TZ = ZoneInfo(DISPLAY_TZ_NAME)


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    return utc_now().replace(tzinfo=None)


def to_utc(dt: datetime) -> datetime:
    """Return a timezone-aware UTC datetime. Naive values are treated as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_utc_naive(dt: datetime) -> datetime:
    """Naive UTC for SQLite DateTime columns."""
    return to_utc(dt).replace(tzinfo=None)


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return to_utc(dt)


def to_iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return to_utc(dt).isoformat().replace("+00:00", "Z")


def today_in_display_tz() -> date:
    return datetime.now(DISPLAY_TZ).date()


def parse_iso_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return to_utc(value)
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return to_utc(datetime.fromisoformat(raw))


def format_display_time(value: str | datetime, include_date: bool = False) -> str:
    local = parse_iso_utc(value).astimezone(DISPLAY_TZ)
    hour = local.strftime("%I").lstrip("0") or "0"
    minute = local.strftime("%M")
    ampm = local.strftime("%p")
    clock = f"{hour}:{minute} {ampm}"
    if not include_date:
        return clock
    return f"{local.strftime('%b')} {local.day}, {clock}"


def display_day_bounds_utc_naive(day: date | None = None) -> tuple[datetime, datetime]:
    """Inclusive UTC (naive) bounds for a calendar day in Asia/Kolkata."""
    day = day or today_in_display_tz()
    start_local = datetime.combine(day, time.min, tzinfo=DISPLAY_TZ)
    end_local = datetime.combine(day, time.max, tzinfo=DISPLAY_TZ)
    return to_utc_naive(start_local), to_utc_naive(end_local)
