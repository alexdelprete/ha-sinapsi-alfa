"""Repair issues for Sinapsi Alfa integration.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from __future__ import annotations

import logging

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Issue IDs
ISSUE_CONNECTION_FAILED = "connection_failed"
ISSUE_RECOVERY_SUCCESS = "recovery_success"
ISSUE_RECOVERY_SUCCESS_NO_SCRIPT = "recovery_success_no_script"


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow to handle fixing a repair issue.

    This is called when a user clicks on a fixable repair issue.
    For recovery notifications, we use ConfirmRepairFlow which shows
    a simple confirmation dialog to acknowledge and dismiss the issue.

    Args:
        hass: HomeAssistant instance
        issue_id: The issue ID (e.g., "recovery_success_<entry_id>")
        data: Optional data associated with the issue

    Returns:
        A RepairsFlow instance to handle the fix

    """
    # All our fixable issues use ConfirmRepairFlow for simple acknowledgment
    return ConfirmRepairFlow()


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
    if script_name and script_executed_at:
        translation_key = ISSUE_RECOVERY_SUCCESS
        placeholders = {
            "device_name": device_name,
            "started_at": started_at,
            "script_executed_at": script_executed_at,
            "ended_at": ended_at,
            "downtime": downtime,
            "script_name": script_name,
        }
    else:
        translation_key = ISSUE_RECOVERY_SUCCESS_NO_SCRIPT
        placeholders = {
            "device_name": device_name,
            "started_at": started_at,
            "ended_at": ended_at,
            "downtime": downtime,
        }

    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{translation_key}_{entry_id}",
        is_fixable=True,  # User can dismiss by clicking "Mark as resolved"
        is_persistent=True,  # Survives HA restart, requires user acknowledgment
        severity=ir.IssueSeverity.WARNING,
        translation_key=translation_key,
        translation_placeholders=placeholders,
    )
    _LOGGER.debug(
        "Created recovery notification for %s (started: %s, ended: %s, downtime: %s, script: %s)",
        device_name,
        started_at,
        ended_at,
        downtime,
        script_name,
    )
