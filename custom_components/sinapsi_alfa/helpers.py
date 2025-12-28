"""Helper functions for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from datetime import UTC, datetime
import ipaddress
import logging
import re
from typing import Any


def host_valid(host: str) -> bool:
    """Validate if hostname or IP address is valid."""
    try:
        # Check if it's a valid IP address (IPv4 or IPv6)
        return ipaddress.ip_address(host).version in (4, 6)
    except ValueError:
        # Not a valid IP address, validate as hostname
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

    return datetime.fromtimestamp(timestamp=unix_timestamp, tz=UTC).astimezone().isoformat()


def log_debug(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized debug logging with context."""
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.debug("%s: %s", context_str, message)


def log_info(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized info logging with context."""
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.info("%s: %s", context_str, message)


def log_warning(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized warning logging with context."""
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.warning("%s: %s", context_str, message)


def log_error(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized error logging with context."""
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.error("%s: %s", context_str, message)
