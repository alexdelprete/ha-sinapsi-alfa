"""Data Update Coordinator for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SinapsiAlfaAPI
from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SKIP_MAC_DETECTION,
    CONF_TIMEOUT,
    DEFAULT_SKIP_MAC_DETECTION,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MAX_TIMEOUT,
    MIN_SCAN_INTERVAL,
    MIN_TIMEOUT,
)
from .helpers import log_debug
from .repairs import create_connection_issue, delete_connection_issue

_LOGGER = logging.getLogger(__name__)

# Number of consecutive failures before creating repair issue
FAILURES_BEFORE_REPAIR_ISSUE = 3


class SinapsiAlfaCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize data update coordinator."""

        # Get initial config from data (set during setup, changed via reconfigure flow)
        self.conf_name = config_entry.data[CONF_NAME]
        self.conf_host = config_entry.data[CONF_HOST]
        self.conf_port = int(config_entry.data[CONF_PORT])
        self.skip_mac_detection = config_entry.data.get(
            CONF_SKIP_MAC_DETECTION, DEFAULT_SKIP_MAC_DETECTION
        )

        # Get runtime options from options (changed via options flow)
        # Migration ensures these exist in options for existing installs
        self.scan_interval = int(config_entry.options[CONF_SCAN_INTERVAL])
        self.timeout = int(config_entry.options[CONF_TIMEOUT])

        # enforce scan_interval bounds
        if self.scan_interval < MIN_SCAN_INTERVAL:
            self.scan_interval = MIN_SCAN_INTERVAL
        elif self.scan_interval > MAX_SCAN_INTERVAL:
            self.scan_interval = MAX_SCAN_INTERVAL
        # set coordinator update interval
        self.update_interval = timedelta(seconds=self.scan_interval)

        # enforce timeout bounds
        if self.timeout < MIN_TIMEOUT:
            self.timeout = MIN_TIMEOUT
        elif self.timeout > MAX_TIMEOUT:
            self.timeout = MAX_TIMEOUT
        log_debug(
            _LOGGER,
            "__init__",
            "Scan Interval configured",
            scan_interval=self.scan_interval,
            update_interval=self.update_interval,
        )
        log_debug(
            _LOGGER,
            "__init__",
            "Timeout configured",
            timeout=self.timeout,
        )

        # set update method and interval for coordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,  # type: ignore[arg-type]
            update_interval=self.update_interval,
        )

        self.last_update_time = datetime.now()
        self.last_update_success = True
        self._consecutive_failures = 0
        self._repair_issue_created = False
        self._entry_id = config_entry.entry_id

        self.api = SinapsiAlfaAPI(
            hass,
            self.conf_name,
            self.conf_host,
            self.conf_port,
            self.scan_interval,
            self.timeout,
            self.skip_mac_detection,
        )

        log_debug(_LOGGER, "__init__", "Coordinator Config Data", data=config_entry.data)
        log_debug(
            _LOGGER,
            "__init__",
            "Coordinator initialized",
            host=self.conf_host,
            port=self.conf_port,
            scan_interval=self.scan_interval,
        )

    async def async_update_data(self) -> bool:
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
            # Reset failure counter on success
            self._consecutive_failures = 0
            # Delete repair issue if it was created
            if self._repair_issue_created:
                delete_connection_issue(self.hass, self._entry_id)
                self._repair_issue_created = False
                log_debug(
                    _LOGGER,
                    "async_update_data",
                    "Connection restored, repair issue deleted",
                )
        except Exception as ex:
            self.last_update_status = False
            self._consecutive_failures += 1
            log_debug(
                _LOGGER,
                "async_update_data",
                "Update error",
                error=ex,
                consecutive_failures=self._consecutive_failures,
                time=self.last_update_time,
            )
            # Create repair issue after repeated failures
            if (
                self._consecutive_failures >= FAILURES_BEFORE_REPAIR_ISSUE
                and not self._repair_issue_created
            ):
                create_connection_issue(
                    self.hass,
                    self._entry_id,
                    self.conf_name,
                    self.conf_host,
                    self.conf_port,
                )
                self._repair_issue_created = True
                log_debug(
                    _LOGGER,
                    "async_update_data",
                    "Repair issue created after repeated failures",
                    failures=self._consecutive_failures,
                )
            raise UpdateFailed from ex
        return self.last_update_status
