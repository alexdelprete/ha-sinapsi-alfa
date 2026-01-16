"""Helper functions for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from datetime import UTC, datetime
import ipaddress
import logging
import re
import socket
from typing import Any

from homeassistant.core import HomeAssistant


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


async def resolve_host_to_ip(hass: HomeAssistant, host: str) -> str | None:
    """Resolve a hostname or FQDN to an IP address.

    The Alfa device only supports one Modbus TCP client at a time.
    This function is used to compare hosts configured in different integrations
    to detect conflicts even when one uses IP and another uses hostname.

    Args:
        hass: Home Assistant instance
        host: Hostname, FQDN, or IP address

    Returns:
        IP address string, or None if resolution fails

    """
    # If already an IP address, return as-is
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return host

    # Resolve hostname to IP using executor to avoid blocking
    try:
        return await hass.async_add_executor_job(socket.gethostbyname, host)
    except socket.gaierror:
        return None


async def check_modbus_conflict(hass: HomeAssistant, host: str) -> str | None:
    """Check if built-in Modbus integration is configured for the same host.

    The Alfa device only supports one Modbus TCP client at a time.
    If the built-in Modbus integration is configured for this host,
    both integrations will interfere with each other.

    Compares resolved IP addresses to handle IP vs hostname differences
    (e.g., 192.168.1.100 vs alfa.local pointing to the same device).

    Args:
        hass: Home Assistant instance
        host: The host/IP to check for conflicts

    Returns:
        The conflicting Modbus host string if conflict found, None otherwise

    """
    # Resolve our host to IP for comparison
    our_ip = await resolve_host_to_ip(hass, host)
    if not our_ip:
        # Can't resolve our host, skip conflict check
        return None

    modbus_entries = hass.config_entries.async_entries(domain="modbus")
    for entry in modbus_entries:
        modbus_host = entry.data.get("host")
        if not modbus_host:
            continue

        # Resolve modbus host to IP
        modbus_ip = await resolve_host_to_ip(hass, modbus_host)
        if modbus_ip and modbus_ip == our_ip:
            return modbus_host  # Return the conflicting host for the error message

    return None
