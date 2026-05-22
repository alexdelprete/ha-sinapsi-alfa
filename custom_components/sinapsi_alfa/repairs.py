"""Repair issues for Sinapsi Alfa integration.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Issue IDs
ISSUE_CONNECTION_FAILED = "connection_failed"
ISSUE_MODBUS_CONFLICT = "modbus_conflict"
ISSUE_DEVICE_WARMUP = "device_warmup"

# Notification IDs
NOTIFICATION_RECOVERY = "recovery"
NOTIFICATION_WARMUP_RECOVERED = "warmup_recovered"


def create_connection_issue(
    hass: HomeAssistant,
    entry_id: str,
    device_name: str,
    host: str,
    port: int,
) -> None:
    """Create a repair issue for connection failure.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID
        device_name: Name of the device
        host: Device host/IP
        port: Device port

    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_CONNECTION_FAILED}_{entry_id}",
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_CONNECTION_FAILED,
        translation_placeholders={
            "device_name": device_name,
            "host": host,
            "port": str(port),
        },
    )
    _LOGGER.debug("Created repair issue for connection failure: %s", device_name)


def delete_connection_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the connection failure repair issue.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID

    """
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_CONNECTION_FAILED}_{entry_id}")
    _LOGGER.debug("Deleted repair issue for entry: %s", entry_id)


def create_modbus_conflict_issue(
    hass: HomeAssistant,
    entry_id: str,
    device_name: str,
    our_host: str,
    modbus_host: str,
) -> None:
    """Create a repair issue for Modbus integration conflict.

    The Alfa device only supports one Modbus TCP client at a time.
    This issue is created when the built-in Modbus integration is also
    configured for the same device.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID
        device_name: Name of the device
        our_host: Host configured in this integration
        modbus_host: Host configured in the Modbus integration

    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_MODBUS_CONFLICT}_{entry_id}",
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_MODBUS_CONFLICT,
        translation_placeholders={
            "device_name": device_name,
            "host": our_host,
            "modbus_host": modbus_host,
        },
    )
    _LOGGER.debug(
        "Created Modbus conflict repair issue for %s (our: %s, modbus: %s)",
        device_name,
        our_host,
        modbus_host,
    )


def delete_modbus_conflict_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the Modbus conflict repair issue.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID

    """
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_MODBUS_CONFLICT}_{entry_id}")
    _LOGGER.debug("Deleted Modbus conflict repair issue for entry: %s", entry_id)


def create_warmup_issue(hass: HomeAssistant, entry_id: str, device_name: str) -> None:
    """Create a repair issue for the device warm-up phase.

    Raised when the device returns zeroed registers after a restart/reboot. Unlike
    the connection issue this is an expected transient (severity WARNING) and is not
    persisted across HA restarts. Idempotent — safe to call on every warm-up poll.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID
        device_name: Name of the device

    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_DEVICE_WARMUP}_{entry_id}",
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_DEVICE_WARMUP,
        translation_placeholders={"device_name": device_name},
    )
    _LOGGER.debug("Created repair issue for device warm-up: %s", device_name)


def delete_warmup_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the device warm-up repair issue.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID

    """
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_DEVICE_WARMUP}_{entry_id}")
    _LOGGER.debug("Deleted device warm-up repair issue for entry: %s", entry_id)


def is_warmup_issue_active(hass: HomeAssistant, entry_id: str) -> bool:
    """Return True if the device warm-up repair issue currently exists.

    The issue registry is the source of truth for warm-up state: the coordinator is
    rebuilt on every config-entry setup retry, so instance attributes cannot track it.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID

    """
    return (
        ir.async_get(hass).async_get_issue(DOMAIN, f"{ISSUE_DEVICE_WARMUP}_{entry_id}") is not None
    )


def create_warmup_recovery_notification(
    hass: HomeAssistant, entry_id: str, device_name: str
) -> None:
    """Create a persistent notification when the device finishes warming up.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID
        device_name: Name of the device

    """
    message = (
        f"**{device_name}** has finished warming up after a restart. "
        "Its meter registers are populated again and the integration has resumed "
        "publishing data."
    )
    title = f"{device_name} finished warming up"
    notification_id = f"{DOMAIN}_{NOTIFICATION_WARMUP_RECOVERED}_{entry_id}"

    hass.async_create_task(
        hass.services.async_call(
            domain="persistent_notification",
            service="create",
            service_data={
                "title": title,
                "message": message,
                "notification_id": notification_id,
            },
        )
    )
    _LOGGER.debug("Created warm-up recovery notification for %s", device_name)


def create_recovery_notification(
    hass: HomeAssistant,
    entry_id: str,
    device_name: str,
    started_at: str,
    ended_at: str,
    downtime: str,
    script_name: str | None = None,
    script_executed_at: str | None = None,
) -> None:
    """Create a persistent notification for device recovery.

    Uses persistent_notification service instead of repair issues to ensure
    the full message with timestamps is displayed properly when clicked.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID
        device_name: Name of the device
        started_at: Time when failure started (locale-aware format)
        ended_at: Time when device recovered (locale-aware format)
        downtime: Total downtime in compact format (e.g., "5m 23s")
        script_name: Name of the recovery script (if executed)
        script_executed_at: Time when script was executed (if executed)

    """
    # Build the notification message
    message_lines = [
        f"**{device_name}** is now responding again.",
        "",
        f"**Failure started:** {started_at}",
    ]

    if script_name and script_executed_at:
        message_lines.append(f"**Script executed:** {script_executed_at}")
        message_lines.append(f"**Recovery script:** {script_name}")

    message_lines.extend(
        [
            f"**Recovery time:** {ended_at}",
            f"**Total downtime:** {downtime}",
        ]
    )

    message = "\n".join(message_lines)
    title = f"{device_name} has recovered"
    notification_id = f"{DOMAIN}_{NOTIFICATION_RECOVERY}_{entry_id}"

    # Use persistent_notification service for immediate display
    hass.async_create_task(
        hass.services.async_call(
            domain="persistent_notification",
            service="create",
            service_data={
                "title": title,
                "message": message,
                "notification_id": notification_id,
            },
        )
    )

    _LOGGER.debug(
        "Created recovery notification for %s (started: %s, ended: %s, downtime: %s, script: %s)",
        device_name,
        started_at,
        ended_at,
        downtime,
        script_name,
    )
