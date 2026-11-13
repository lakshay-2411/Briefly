from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import settings


def next_run_at(time_of_day: time, tz_name: str, now: datetime | None = None) -> datetime:
    """Next UTC moment to start generating: the user's local time minus the lead time."""
    tz = ZoneInfo(tz_name)
    now = now or datetime.now(timezone.utc)
    lead = timedelta(minutes=settings.generation_lead_minutes)
    local_date = now.astimezone(tz).date()
    # Check yesterday too: with lead time crossing midnight, a run "for tomorrow" can start today.
    for offset in (-1, 0, 1, 2):
        day = local_date + timedelta(days=offset)
        run = datetime.combine(day, time_of_day, tzinfo=tz) - lead
        if run > now:
            return run.astimezone(timezone.utc)
    raise AssertionError("unreachable")
