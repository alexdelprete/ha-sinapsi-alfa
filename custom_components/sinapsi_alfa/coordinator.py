"""Data Update Coordinator for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SinapsiAlfaAPI
from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)


class SinapsiAlfaCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize data update coordinator."""

        # get parameters from user config
        self.conf_name = config_entry.data.get(CONF_NAME)
        self.conf_host = config_entry.data.get(CONF_HOST)
        self.conf_port = int(config_entry.data.get(CONF_PORT))
        self.scan_interval = int(
            config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        # enforce scan_interval bounds
        if self.scan_interval < MIN_SCAN_INTERVAL:
            self.scan_interval = MIN_SCAN_INTERVAL
        elif self.scan_interval > MAX_SCAN_INTERVAL:
            self.scan_interval = MAX_SCAN_INTERVAL
        # set coordinator update interval
        self.update_interval = timedelta(seconds=self.scan_interval)
        log_debug(
            _LOGGER,
            "__init__",
            "Scan Interval configured",
            scan_interval=self.scan_interval,
            update_interval=self.update_interval,
        )

        # set update method and interval for coordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=self.update_interval,
        )

        self.last_update_time = datetime.now()
        self.last_update_success = True

        self.api = SinapsiAlfaAPI(
            hass,
            self.conf_name,
            self.conf_host,
            self.conf_port,
            self.scan_interval,
        )

        log_debug(
            _LOGGER, "__init__", "Coordinator Config Data", data=config_entry.data
        )
        log_debug(
            _LOGGER,
            "__init__",
            "Coordinator initialized",
            host=self.conf_host,
            port=self.conf_port,
            scan_interval=self.scan_interval,
        )

    async def async_update_data(self):
        """Update data method."""
        log_debug(_LOGGER, "async_update_data", "Update started", time=datetime.now())
        try:
            self.last_update_status = await self.api.async_get_data()
            self.last_update_time = datetime.now()
            log_debug(
                _LOGGER,
                "async_update_data",
                "Update completed",
                time=self.last_update_time,
            )
        except Exception as ex:
            self.last_update_status = False
            log_debug(
                _LOGGER,
                "async_update_data",
                "Update error",
                error=ex,
                time=self.last_update_time,
            )
            raise UpdateFailed from ex
        return self.last_update_status
