"""Sensor Platform Device for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SinapsiAlfaConfigEntry
from .const import CONF_NAME, DOMAIN, SENSOR_ENTITIES
from .coordinator import SinapsiAlfaCoordinator
from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: SinapsiAlfaConfigEntry, async_add_entities
):
    """Sensor Platform setup."""

    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator: SinapsiAlfaCoordinator = config_entry.runtime_data.coordinator

    log_debug(
        _LOGGER, "async_setup_entry", "Name", name=config_entry.data.get(CONF_NAME)
    )
    log_debug(
        _LOGGER,
        "async_setup_entry",
        "Manufacturer",
        manufacturer=coordinator.api.data["manufact"],
    )
    log_debug(
        _LOGGER, "async_setup_entry", "Model", model=coordinator.api.data["model"]
    )
    log_debug(_LOGGER, "async_setup_entry", "Serial", serial=coordinator.api.data["sn"])

    sensors = [
        SinapsiAlfaSensor(
            coordinator,
            sensor["name"],
            sensor["key"],
            sensor["icon"],
            sensor["device_class"],
            sensor["state_class"],
            sensor["unit"],
        )
        for sensor in SENSOR_ENTITIES
        if coordinator.api.data[sensor["key"]] is not None
    ]

    async_add_entities(sensors)

    return True


class SinapsiAlfaSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sinapsi Alfa sensor."""

    def __init__(self, coordinator, name, key, icon, device_class, state_class, unit):
        """Class Initializitation."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._name = name
        self._key = key
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._unit_of_measurement = unit
        self._device_name = self._coordinator.api.name
        self._device_host = self._coordinator.api.host
        self._device_model = self._coordinator.api.data["model"]
        self._device_manufact = self._coordinator.api.data["manufact"]
        self._device_sn = self._coordinator.api.data["sn"]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch new state data for the sensor."""
        self._state = self._coordinator.api.data[self._key]
        self.async_write_ha_state()
        # write debug log only on first sensor to avoid spamming the log
        if self.name == "Potenza Prelevata":
            log_debug(
                _LOGGER,
                "_handle_coordinator_update",
                "Sensors state written to state machine",
            )

    # when has_entity_name is True, the resulting entity name will be: {device_name}_{self._name}
    @property
    def has_entity_name(self):
        """Return the name state."""
        return True

    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the sensor icon."""
        return self._icon

    @property
    def device_class(self):
        """Return the sensor device_class."""
        return self._device_class

    @property
    def state_class(self):
        """Return the sensor state_class."""
        return self._state_class

    @property
    def entity_category(self):
        """Return the sensor entity_category."""
        if self._state_class is None:
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._key in self._coordinator.api.data:
            return self._coordinator.api.data[self._key]
        return None

    @property
    def state_attributes(self) -> dict[str, Any] | None:
        """Return the attributes."""
        return None

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}_{self._device_sn}_{self._key}"

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "configuration_url": f"http://{self._device_host}",
            "hw_version": None,
            "identifiers": {(DOMAIN, self._device_sn)},
            "manufacturer": self._device_manufact,
            "model": self._device_model,
            "name": self._device_name,
            "serial_number": self._device_sn,
            "sw_version": None,
            "via_device": None,
        }
