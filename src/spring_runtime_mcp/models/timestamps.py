"""Bounded RFC3339 parsing shared by contracts and runtime evidence.

Keep fractional precision and a leap-second ordering slot. Duration arithmetic
involving an explicit leap second remains unknown without a trusted history.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

_TIMESTAMP = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]"
    r"([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?"
    r"([Zz]|[+-][0-9]{2}:[0-9]{2})"
)


@dataclass(frozen=True, order=True)
class Timestamp:
    second: datetime
    leap: bool
    fraction: Decimal

    def milliseconds_since(self, earlier: Timestamp) -> float | None:
        if self.leap or earlier.leap:
            return None
        delta = self.second - earlier.second
        seconds = Decimal(delta.days * 86400 + delta.seconds)
        return float((seconds + self.fraction - earlier.fraction) * 1000)


def parse_rfc3339(value: object) -> Timestamp | None:
    if not isinstance(value, str) or len(value) > 64:
        return None
    match = _TIMESTAMP.fullmatch(value)
    if match is None:
        return None
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    offset = match[8]
    try:
        zone = UTC
        if offset not in ("Z", "z"):
            hours, minutes = int(offset[1:3]), int(offset[4:6])
            if hours > 23 or minutes > 59:
                return None
            zone = timezone(
                timedelta(
                    minutes=(hours * 60 + minutes) * (1 if offset[0] == "+" else -1)
                )
            )
        if second > 60:
            return None
        instant = datetime(
            year, month, day, hour, minute, min(second, 59), tzinfo=zone
        ).astimezone(UTC)
    except (ValueError, OverflowError):
        return None
    leap = second == 60
    # RFC3339 permits insertions at UTC month ends. Validate the placement;
    # do not claim knowledge of a historical or future insertion schedule.
    if leap and (
        instant.hour != 23
        or instant.minute != 59
        or instant.day != calendar.monthrange(instant.year, instant.month)[1]
    ):
        return None
    return Timestamp(instant, leap, Decimal("0" + (match[7] or "")))
