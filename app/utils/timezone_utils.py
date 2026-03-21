"""
Timezone utilities for IST (Indian Standard Time) conversion.
IST is UTC+5:30.
"""

from datetime import datetime, timezone, timedelta
from typing import Tuple

# IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST datetime."""
    if utc_dt is None:
        return None
    # Make UTC-aware if naive
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    # Convert to IST
    return utc_dt.astimezone(IST)


def ist_to_utc(ist_dt: datetime) -> datetime:
    """Convert IST datetime to UTC datetime."""
    if ist_dt is None:
        return None
    # Make IST-aware if naive
    if ist_dt.tzinfo is None:
        ist_dt = ist_dt.replace(tzinfo=IST)
    # Convert to UTC
    return ist_dt.astimezone(timezone.utc)


def now_ist() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def now_utc() -> datetime:
    """Get current time in UTC."""
    return datetime.now(timezone.utc)


def parse_time_to_ist(hour: int, minute: int, second: int = 0) -> datetime:
    """Parse time components (hour, minute, second) to IST datetime for today."""
    now = now_ist()
    return now.replace(hour=hour, minute=minute, second=second, microsecond=0)


def time_string_to_minutes(time_str: str) -> int:
    """Convert time string 'HH:MM' or 'H:MM' to minutes since midnight."""
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours * 60 + minutes
    except (ValueError, IndexError):
        raise ValueError(f"Invalid time format: {time_str}. Use HH:MM or H:MM")


def minutes_to_time_string(minutes: int) -> str:
    """Convert minutes since midnight to 'HH:MM' format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def is_time_between(current_time: datetime, start_time: datetime, end_time: datetime) -> bool:
    """Check if current_time is between start_time and end_time (all should be IST)."""
    current_minutes = current_time.hour * 60 + current_time.minute
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    
    # Handle case where end time is before start time (e.g., no wrap around)
    return start_minutes <= current_minutes < end_minutes
