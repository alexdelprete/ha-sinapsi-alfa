"""Config Flow for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from .api import SinapsiAlfaAPI, SinapsiConnectionError, SinapsiModbusError
from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SKIP_MAC_DETECTION,
    CONF_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SKIP_MAC_DETECTION,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAX_PORT,
    MAX_SCAN_INTERVAL,
    MIN_PORT,
    MIN_SCAN_INTERVAL,
)
from .helpers import host_valid, log_debug, log_error

_LOGGER = logging.getLogger(__name__)


@callback
def get_host_from_config(hass: HomeAssistant):
    """Return the hosts already configured."""
    return {
        config_entry.data.get(CONF_HOST)
        for config_entry in hass.config_entries.async_entries(DOMAIN)
    }


class SinapsiAlfaConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Sinapsi Alfa config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Initiate Options Flow Instance."""
        return SinapsiAlfaOptionsFlow(config_entry)

    def _host_in_configuration_exists(self, host) -> bool:
        """Return True if host exists in configuration."""
        if host in get_host_from_config(self.hass):
            return True
        return False

    async def get_unique_id(
        self, name, host, port, scan_interval, timeout, skip_mac_detection
    ):
        """Return device serial number."""
        log_debug(_LOGGER, "get_unique_id", "Test connection", host=host, port=port)
        try:
            log_debug(_LOGGER, "get_unique_id", "Creating API Client")
            self.api = SinapsiAlfaAPI(
                self.hass, name, host, port, scan_interval, timeout, skip_mac_detection
            )
            log_debug(_LOGGER, "get_unique_id", "API Client created: calling get data")
            self.api_data = await self.api.async_get_data()
            log_debug(_LOGGER, "get_unique_id", "API Client: get data")
            log_debug(_LOGGER, "get_unique_id", "API Client Data", data=self.api_data)
            return self.api.data["sn"]
        except (
            SinapsiConnectionError,
            SinapsiModbusError,
        ) as connerr:
            log_error(
                _LOGGER,
                "get_unique_id",
                "Failed to connect",
                host=host,
                port=port,
                error=connerr,
            )
            return False

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            name = user_input[CONF_NAME]
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            timeout = user_input[CONF_TIMEOUT]
            skip_mac_detection = user_input.get(
                CONF_SKIP_MAC_DETECTION, DEFAULT_SKIP_MAC_DETECTION
            )

            if self._host_in_configuration_exists(host):
                errors[CONF_HOST] = "Device Already Configured"
            elif not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "Invalid Host IP"
            else:
                uid = await self.get_unique_id(
                    name, host, port, scan_interval, timeout, skip_mac_detection
                )
                if uid is not False:
                    log_debug(_LOGGER, "async_step_user", "Device unique id", uid=uid)
                    # Assign a unique ID to the flow and abort the flow
                    # if another flow with the same unique ID is in progress
                    await self.async_set_unique_id(uid)

                    # Abort the flow if a config entry with the same unique ID exists
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input[CONF_NAME], data=user_input
                    )

                errors[CONF_HOST] = "Connection to device failed (S/N not retreived)"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=DEFAULT_NAME,
                    ): cv.string,
                    vol.Required(
                        CONF_HOST,
                    ): cv.string,
                    vol.Required(
                        CONF_PORT,
                        default=DEFAULT_PORT,
                    ): vol.All(vol.Coerce(int), vol.Clamp(min=MIN_PORT, max=MAX_PORT)),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=DEFAULT_SCAN_INTERVAL,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Required(
                        CONF_TIMEOUT,
                        default=DEFAULT_TIMEOUT,
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_SKIP_MAC_DETECTION,
                        default=DEFAULT_SKIP_MAC_DETECTION,
                    ): cv.boolean,
                },
            ),
            errors=errors,
        )


class SinapsiAlfaOptionsFlow(OptionsFlow):
    """Config flow options handler."""

    VERSION = 1

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize option flow instance."""
        self.data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=config_entry.data.get(CONF_HOST),
                ): cv.string,
                vol.Required(
                    CONF_PORT,
                    default=config_entry.data.get(CONF_PORT),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=MIN_PORT, max=MAX_PORT)),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=config_entry.data.get(CONF_SCAN_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Clamp(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Required(
                    CONF_TIMEOUT,
                    default=config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                ): cv.positive_int,
                vol.Optional(
                    CONF_SKIP_MAC_DETECTION,
                    default=config_entry.data.get(
                        CONF_SKIP_MAC_DETECTION, DEFAULT_SKIP_MAC_DETECTION
                    ),
                ): cv.boolean,
            }
        )

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Manage the options."""

        if user_input is not None:
            # complete non-edited entries before update (ht @PeteRage)
            if CONF_NAME in self.config_entry.data:
                user_input[CONF_NAME] = self.config_entry.data.get(CONF_NAME)

            # write updated config entries (ht @PeteRage / @fuatakgun)
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input, options=self.config_entry.options
            )
            self.async_abort(reason="configuration updated")

            # write empty options entries (ht @PeteRage / @fuatakgun)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="init", data_schema=self.data_schema)
