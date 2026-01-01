"""Config Flow for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
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
    MAX_TIMEOUT,
    MIN_PORT,
    MIN_SCAN_INTERVAL,
    MIN_TIMEOUT,
)
from .helpers import host_valid, log_debug, log_error

_LOGGER = logging.getLogger(__name__)


@callback
def get_host_from_config(hass: HomeAssistant) -> set[str | None]:
    """Return the hosts already configured."""
    return {
        config_entry.data.get(CONF_HOST)
        for config_entry in hass.config_entries.async_entries(DOMAIN)
    }


class SinapsiAlfaConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Sinapsi Alfa config flow."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "SinapsiAlfaOptionsFlow":
        """Initiate Options Flow Instance."""
        return SinapsiAlfaOptionsFlow()

    def _host_in_configuration_exists(self, host: str | None) -> bool:
        """Return True if host exists in configuration."""
        return host in get_host_from_config(self.hass)

    async def _test_connection(
        self,
        name: str,
        host: str,
        port: int,
        scan_interval: int,
        timeout: int,
        skip_mac_detection: bool,
    ) -> str | bool:
        """Test connection and return serial number or False on failure."""
        log_debug(_LOGGER, "_test_connection", "Test connection", host=host, port=port)
        try:
            log_debug(_LOGGER, "_test_connection", "Creating API Client")
            api = SinapsiAlfaAPI(
                self.hass, name, host, port, scan_interval, timeout, skip_mac_detection
            )
            log_debug(_LOGGER, "_test_connection", "API Client created: calling get data")
            await api.async_get_data()
            log_debug(_LOGGER, "_test_connection", "API Client: get data")
            log_debug(_LOGGER, "_test_connection", "API Client Data", data=api.data)
            return api.data["sn"]
        except (
            SinapsiConnectionError,
            SinapsiModbusError,
        ) as connerr:
            log_error(
                _LOGGER,
                "_test_connection",
                "Failed to connect",
                host=host,
                port=port,
                error=connerr,
            )
            return False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_NAME]
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            timeout = user_input[CONF_TIMEOUT]
            skip_mac_detection = user_input.get(CONF_SKIP_MAC_DETECTION, DEFAULT_SKIP_MAC_DETECTION)

            if self._host_in_configuration_exists(host):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                uid = await self._test_connection(
                    name, host, port, scan_interval, timeout, skip_mac_detection
                )
                if uid is not False:
                    log_debug(_LOGGER, "async_step_user", "Device unique id", uid=uid)
                    await self.async_set_unique_id(uid)
                    self._abort_if_unique_id_configured()

                    # Separate data (initial config) and options (runtime tuning)
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_NAME: name,
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_SKIP_MAC_DETECTION: skip_mac_detection,
                        },
                        options={
                            CONF_SCAN_INTERVAL: scan_interval,
                            CONF_TIMEOUT: timeout,
                        },
                    )

                errors[CONF_HOST] = "cannot_connect"

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
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_TIMEOUT, max=MAX_TIMEOUT),
                    ),
                    vol.Optional(
                        CONF_SKIP_MAC_DETECTION,
                        default=DEFAULT_SKIP_MAC_DETECTION,
                    ): cv.boolean,
                },
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_NAME]
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            skip_mac_detection = user_input.get(CONF_SKIP_MAC_DETECTION, DEFAULT_SKIP_MAC_DETECTION)

            log_debug(
                _LOGGER,
                "async_step_reconfigure",
                "Reconfigure requested",
                name=name,
                host=host,
                port=port,
                skip_mac_detection=skip_mac_detection,
            )

            if not host_valid(host):
                log_debug(_LOGGER, "async_step_reconfigure", "Invalid host", host=host)
                errors[CONF_HOST] = "invalid_host"
            else:
                # Test connection with new settings (use existing options for scan_interval/timeout)
                scan_interval = reconfigure_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
                timeout = reconfigure_entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

                uid = await self._test_connection(
                    name, host, port, scan_interval, timeout, skip_mac_detection
                )
                if uid is not False:
                    # Verify unique ID matches before updating (per HA best practice)
                    await self.async_set_unique_id(uid)
                    self._abort_if_unique_id_mismatch()

                    log_debug(
                        _LOGGER,
                        "async_step_reconfigure",
                        "Connection test passed, applying reconfigure",
                        uid=uid,
                    )
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        title=name,
                        data_updates={
                            CONF_NAME: name,
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_SKIP_MAC_DETECTION: skip_mac_detection,
                        },
                    )

                log_debug(_LOGGER, "async_step_reconfigure", "Connection test failed")
                errors[CONF_HOST] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=reconfigure_entry.data.get(CONF_NAME, DEFAULT_NAME),
                    ): cv.string,
                    vol.Required(
                        CONF_HOST,
                        default=reconfigure_entry.data.get(CONF_HOST),
                    ): cv.string,
                    vol.Required(
                        CONF_PORT,
                        default=reconfigure_entry.data.get(CONF_PORT, DEFAULT_PORT),
                    ): vol.All(vol.Coerce(int), vol.Clamp(min=MIN_PORT, max=MAX_PORT)),
                    vol.Optional(
                        CONF_SKIP_MAC_DETECTION,
                        default=reconfigure_entry.data.get(
                            CONF_SKIP_MAC_DETECTION, DEFAULT_SKIP_MAC_DETECTION
                        ),
                    ): cv.boolean,
                },
            ),
            errors=errors,
        )


class SinapsiAlfaOptionsFlow(OptionsFlowWithReload):
    """Config flow options handler with auto-reload."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            log_debug(
                _LOGGER,
                "async_step_init",
                "Options updated",
                scan_interval=user_input.get(CONF_SCAN_INTERVAL),
                timeout=user_input.get(CONF_TIMEOUT),
            )
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Required(
                        CONF_TIMEOUT,
                        default=self.config_entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_TIMEOUT, max=MAX_TIMEOUT),
                    ),
                },
            ),
        )
