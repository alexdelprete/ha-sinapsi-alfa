"""Helper functions for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import ipaddress
import re
from datetime import UTC, datetime


def host_valid(host):
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version == (4 or 6):
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))


def unix_timestamp_to_iso8601_local_tz(unix_timestamp: int) -> str:
    """Convert unix timestamp (UTC) to datetime ISO8601 format with local timezone offset.

    Args:
        unix_timestamp (int): Unix timestamp in seconds since the epoch.

    Returns:
        str: ISO8601 formatted datetime string with local timezone offset.

    Example:
        >>> unix_timestamp_to_iso8601_local_tz(1739238065) in CET timezone
        '2025-02-11T02:41:05+01:00'

    """

    return (
        datetime.fromtimestamp(timestamp=unix_timestamp, tz=UTC)
        .astimezone()
        .isoformat()
    )
