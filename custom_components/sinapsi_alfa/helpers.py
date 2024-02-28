"""Helper functions for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import ipaddress
import re
import time
from datetime import datetime, timedelta, timezone


def host_valid(host):
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version == (4 or 6):
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))


def get_local_timezone_offset() -> float:
    """Get local timezone offset."""
    # Get the current time in seconds since the epoch
    current_time = time.time()

    # Get the local timezone offset in seconds
    local_timezone_offset_seconds = (
        -time.timezone
        if (time.localtime(current_time).tm_isdst == 0)
        else -time.altzone
    )

    # Convert the offset to hours
    local_timezone_offset_hours = local_timezone_offset_seconds / 3600

    return local_timezone_offset_hours


def unix_timestamp_to_iso8601_local_tz(unix_timestamp: int) -> str:
    """Convert timestamp to ISO8601."""

    # Convert Unix timestamp to datetime object in UTC
    dt_utc = datetime.utcfromtimestamp(unix_timestamp).replace(tzinfo=timezone.utc)  # noqa: UP017

    # Get the local timezone offset
    local_timezone_offset_hours = get_local_timezone_offset()

    # Create a timezone object with the local offset
    local_timezone = timezone(timedelta(hours=local_timezone_offset_hours))

    # Convert UTC datetime to local datetime
    dt_local = dt_utc.astimezone(local_timezone)

    # Format local datetime object as ISO8601 string
    iso8601_format = dt_local.isoformat()

    return iso8601_format
