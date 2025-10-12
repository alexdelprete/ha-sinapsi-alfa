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

    # Register an update listener for config flow options changes
    # Listener is attached when entry loads and automatically detached at unload
    # ref.: https://developers.home-assistant.io/docs/config_entries_options_flow_handler/#signal-updates
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

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


@callback
def async_reload_entry(
    hass: HomeAssistant, config_entry: SinapsiAlfaConfigEntry
) -> None:
    """Reload the config entry."""
    hass.config_entries.async_schedule_reload(config_entry.entry_id)


# Sample migration code in case it's needed
# async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
#     """Migrate an old config_entry."""
#     version = config_entry.version

#     # 1-> 2: Migration format
#     if version == 1:
#         # Get handler to coordinator from config
#         coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA]
#         _LOGGER.debug("Migrating from version %s", version)
#         old_uid = config_entry.unique_id
#         new_uid = coordinator.api.data["mac_address"]
#         if old_uid != new_uid:
#             hass.config_entries.async_update_entry(
#                 config_entry, unique_id=new_uid
#             )
#             _LOGGER.debug("Migration to version %s complete: OLD_UID: %s - NEW_UID: %s", config_entry.version, old_uid, new_uid)
#         if config_entry.unique_id == new_uid:
#             config_entry.version = 2
#             _LOGGER.debug("Migration to version %s complete: NEW_UID: %s", config_entry.version, config_entry.unique_id)
#     return True
