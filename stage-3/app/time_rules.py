"""Timezone, DST, and half-open interval rules for reservations."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .domain import DomainError


def resolve_local(value: str, timezone_name: str) -> datetime:
    """Resolve a YYYY-MM-DDTHH:MM wall time using the first fall-back occurrence."""
    if not isinstance(value, str):
        raise DomainError(422, "invalid_local_time", "invalid local time")
    try:
        local = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        zone = ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise DomainError(422, "invalid_local_time", "invalid local time") from exc

    resolved = local.replace(tzinfo=zone, fold=0)
    # A UTC round trip detects spring-forward wall times that zoneinfo otherwise accepts.
    round_trip = resolved.astimezone(ZoneInfo("UTC")).astimezone(zone)
    if round_trip.replace(tzinfo=None) != local:
        raise DomainError(422, "invalid_local_time", "invalid local time")
    return resolved


def intervals_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """Reservations use [start, end), so a departure can equal the next arrival."""
    return start_a < end_b and start_b < end_a


def has_overlap(start: datetime, end: datetime, intervals: list[tuple[datetime, datetime]]) -> bool:
    return any(intervals_overlap(start, end, other_start, other_end) for other_start, other_end in intervals)


def rfc3339(value: datetime) -> str:
    return value.isoformat(timespec="seconds")
