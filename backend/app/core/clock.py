from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import settings

CHINA_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def _zone() -> tzinfo:
    try:
        return ZoneInfo(settings.app_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        # Windows 的 Python 可能没有系统 tzdata；中国时区没有夏令时，固定 +8 即可
        if settings.app_timezone in {"Asia/Shanghai", "Asia/Chongqing", "PRC"}:
            return CHINA_TZ
        return timezone.utc


def now_local() -> datetime:
    """Naive local datetime used consistently for DB storage and comparisons."""
    return datetime.now(_zone()).replace(tzinfo=None)


def today_local() -> date:
    return now_local().date()
