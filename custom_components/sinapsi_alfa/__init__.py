"""Sinapsi Alfa Integration.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    STARTUP_MESSAGE,
)
from .coordinator import SinapsiAlfaCoordinator
from .helpers import log_debug, log_error, log_info

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# The type alias needs to be suffixed with 'ConfigEntry'
type SinapsiAlfaConfigEntry = ConfigEntry[RuntimeData]


@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry: SinapsiAlfaConfigEntry):
    """Set up integration from a config entry."""
    log_info(_LOGGER, "async_setup_entry", STARTUP_MESSAGE)
    log_debug(_LOGGER, "async_setup_entry", "Setup config_entry", domain=DOMAIN)

    # Initialise the coordinator that manages data updates from your api.
    # This is defined in coordinator.py
    coordinator = SinapsiAlfaCoordinator(hass, config_entry)

    # If the refresh fails, async_config_entry_first_refresh() will
    # raise ConfigEntryNotReady and setup will try again later
    # ref.: https://developers.home-assistant.io/docs/integration_setup_failures
    await coordinator.async_config_entry_first_refresh()

    # Test to see if api initialised correctly, else raise ConfigNotReady to make HA retry setup
    # Change this to match how your api will know if connected or successful update
    if not coordinator.api.data["sn"]:
        raise ConfigEntryNotReady(
            f"Timeout connecting to {config_entry.data.get(CONF_NAME)}"
        )

    # Store coordinator in runtime_data to make it accessible throughout the integration
    config_entry.runtime_data = RuntimeData(coordinator)

    # Note: No manual update listener needed - OptionsFlowWithReload handles reload automatically

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Register device
    async_update_device_registry(hass, config_entry)

    # Return true to denote a successful setup.
    return True


@callback
def async_update_device_registry(
    hass: HomeAssistant, config_entry: SinapsiAlfaConfigEntry
) -> None:
    """Manual device registration."""
    coordinator: SinapsiAlfaCoordinator = config_entry.runtime_data.coordinator
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        hw_version=None,
        configuration_url=f"http://{config_entry.data.get(CONF_HOST)}",
        identifiers={(DOMAIN, coordinator.api.data["sn"])},
        manufacturer=coordinator.api.data["manufact"],
        model=coordinator.api.data["model"],
        name=config_entry.data.get(CONF_NAME),
        serial_number=coordinator.api.data["sn"],
        sw_version=None,
        via_device=None,
    )


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry, device_entry
) -> bool:
    """Delete device if not entities."""
    if DOMAIN in device_entry.identifiers:
        log_error(
            _LOGGER,
            "async_remove_config_entry_device",
            "You cannot delete the device using device delete. Remove the integration instead.",
        )
        return False
    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: SinapsiAlfaConfigEntry
) -> bool:
    """Unload a config entry."""
    log_debug(_LOGGER, "async_unload_entry", "Unload config_entry: started")

    # Unload platforms - only cleanup runtime_data if successful
    # ref.: https://developers.home-assistant.io/blog/2025/02/19/new-config-entry-states/
    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        log_debug(_LOGGER, "async_unload_entry", "Platforms unloaded successfully")
        # Cleanup per-entry resources only if unload succeeded
        await config_entry.runtime_data.coordinator.api.close()
        log_debug(_LOGGER, "async_unload_entry", "Closed API connection")
    else:
        log_debug(
            _LOGGER, "async_unload_entry", "Platform unload failed, skipping cleanup"
        )

    log_debug(
        _LOGGER,
        "async_unload_entry",
        "Unload config_entry: completed",
        unload_ok=unload_ok,
    )
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry to new format."""
    # Handle downgrade scenario (per HA best practice)
    if config_entry.version > 2:
        log_error(
            _LOGGER,
            "async_migrate_entry",
            "Cannot downgrade from future version",
            from_version=config_entry.version,
            current_version=2,
        )
        return False

    log_info(
        _LOGGER,
        "async_migrate_entry",
        "Starting migration",
        from_version=config_entry.version,
        target_version=2,
    )

    if config_entry.version == 1:
        # Version 1 -> 2: Move scan_interval and timeout from data to options
        # This follows HA best practice: data = initial config, options = runtime tuning
        new_data = {**config_entry.data}
        new_options = {**config_entry.options}

        # Extract and log scan_interval migration
        if CONF_SCAN_INTERVAL in new_data:
            scan_interval = new_data.pop(CONF_SCAN_INTERVAL)
            new_options[CONF_SCAN_INTERVAL] = scan_interval
            log_info(
                _LOGGER,
                "async_migrate_entry",
                "Migrated scan_interval from data",
                value=scan_interval,
            )
        else:
            new_options[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL
            log_info(
                _LOGGER,
                "async_migrate_entry",
                "Using default scan_interval",
                value=DEFAULT_SCAN_INTERVAL,
            )

        # Extract and log timeout migration
        if CONF_TIMEOUT in new_data:
            timeout = new_data.pop(CONF_TIMEOUT)
            new_options[CONF_TIMEOUT] = timeout
            log_info(
                _LOGGER,
                "async_migrate_entry",
                "Migrated timeout from data",
                value=timeout,
            )
        else:
            new_options[CONF_TIMEOUT] = DEFAULT_TIMEOUT
            log_info(
                _LOGGER,
                "async_migrate_entry",
                "Using default timeout",
                value=DEFAULT_TIMEOUT,
            )

        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            options=new_options,
            version=2,
        )

        log_info(
            _LOGGER,
            "async_migrate_entry",
            "Migration complete",
            data_keys=list(new_data.keys()),
            options_keys=list(new_options.keys()),
        )

    return True
