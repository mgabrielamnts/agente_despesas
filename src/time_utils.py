from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.config import APP_TIMEZONE


try:
    LOCAL_TIMEZONE = ZoneInfo(APP_TIMEZONE)
except ZoneInfoNotFoundError:
    # Safe fallback for environments without the requested timezone database.
    LOCAL_TIMEZONE = timezone.utc


def local_now() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)


def local_today():
    return local_now().date()
