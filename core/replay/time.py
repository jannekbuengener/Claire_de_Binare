"""
Canonical time helpers for LR-021 replay envelopes.
"""

from datetime import datetime, timezone


def created_at_from_ts_ms(ts_ms: int) -> str:
    """Return UTC ISO-8601 with millisecond precision for the given timestamp."""
    timestamp = int(ts_ms)
    seconds, millis = divmod(timestamp, 1000)
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
        microsecond=millis * 1000
    )
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
