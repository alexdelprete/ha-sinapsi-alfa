"""Diagnostics support for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import SinapsiAlfaConfigEntry
from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SKIP_MAC_DETECTION,
    CONF_TIMEOUT,
    DOMAIN,
    VERSION,
)

# Keys to redact from diagnostics output
TO_REDACT = {
    CONF_HOST,
    "sn",
    "serial_number",
    "ip",
    "mac",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: SinapsiAlfaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data.coordinator

    # Gather configuration data
    config_data = {
        "entry_id": config_entry.entry_id,
        "version": config_entry.version,
        "domain": DOMAIN,
        "integration_version": VERSION,
        "data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "options": {
            CONF_SCAN_INTERVAL: config_entry.options.get(CONF_SCAN_INTERVAL),
            CONF_TIMEOUT: config_entry.options.get(CONF_TIMEOUT),
        },
    }

    # Gather device info
    device_data = {
        "name": config_entry.data.get(CONF_NAME),
        "port": config_entry.data.get(CONF_PORT),
        "skip_mac_detection": config_entry.data.get(CONF_SKIP_MAC_DETECTION),
        "manufacturer": coordinator.api.data.get("manufact"),
        "model": coordinator.api.data.get("model"),
        "serial_number": "**REDACTED**",
    }

    # Gather coordinator state
    coordinator_data = {
        "last_update_success": coordinator.last_update_success,
        "update_interval_seconds": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
    }

    # Gather sensor data (redact sensitive values)
    sensor_data = {}
    if coordinator.api.data:
        for key, value in coordinator.api.data.items():
            if key in TO_REDACT:
                sensor_data[key] = "**REDACTED**"
            else:
                sensor_data[key] = value

    return {
        "config": config_data,
        "device": device_data,
        "coordinator": coordinator_data,
        "sensors": sensor_data,
    }
