"""Sensor Platform Device for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import logging
from typing import Any, cast

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SinapsiAlfaConfigEntry
from .const import CONF_NAME, DOMAIN, RESTORABLE_ENERGY_SENSORS, SENSOR_ENTITIES
from .coordinator import SinapsiAlfaCoordinator
from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SinapsiAlfaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensor Platform setup."""

    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator: SinapsiAlfaCoordinator = config_entry.runtime_data.coordinator

    log_debug(
        _LOGGER,
        "async_setup_entry",
        "Setting up sensors",
        name=config_entry.data.get(CONF_NAME),
        manufacturer=coordinator.api.data["manufact"],
        model=coordinator.api.data["model"],
        serial_number=coordinator.api.data["sn"],
    )

    sensors = []
    for sensor in SENSOR_ENTITIES:
        sensor_def = cast(dict[str, Any], sensor)
        if coordinator.api.data[sensor_def["key"]] is not None:
            sensors.append(
                SinapsiAlfaSensor(
                    coordinator,
                    sensor_def["name"],
                    sensor_def["key"],
                    sensor_def["icon"],
                    sensor_def["device_class"],
                    sensor_def["state_class"],
                    sensor_def["unit"],
                    sensor_def.get("disabled_by_default", False),
                )
            )

    async_add_entities(sensors)


class SinapsiAlfaSensor(CoordinatorEntity[SinapsiAlfaCoordinator], RestoreSensor):
    """Representation of a Sinapsi Alfa sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SinapsiAlfaCoordinator,
        name: str,
        key: str,
        icon: str | None,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        unit: str | None,
        disabled_by_default: bool = False,
    ) -> None:
        """Class Initializitation."""
        super().__init__(coordinator)
        self._coordinator = coordinator
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
        # Use translation key for entity name (translations in translations/*.json)
        self._attr_translation_key = key
        # F1-F6 time band sensors disabled by default (users can enable if needed)
        self._attr_entity_registry_enabled_default = not disabled_by_default
        # Power sensors store 3-decimal kW values (1 W resolution); HA's default
        # display precision for POWER caps at 2 decimals, so ask for 3 explicitly.
        # Energy sensors keep HA's 2-decimal default — 1 Wh granularity would
        # visually clutter large cumulative totals without practical benefit.
        if device_class == SensorDeviceClass.POWER:
            self._attr_suggested_display_precision = 3

    async def async_added_to_hass(self) -> None:
        """Restore the last known value for lifetime energy sensors (issue #206).

        After a Home Assistant restart the API data structure is reset to
        DEFAULT_SENSOR_VALUE (0.0), so the decrease-rejection guard in api.py has no
        real baseline. The Alfa device returns 0 on its cumulative energy registers
        for ~100s after a reboot (warm-up), which would otherwise be published as a
        drop to 0 and double-counted by HA's TOTAL_INCREASING statistics. Seeding the
        restored value back into api.data here (before the first state is written)
        gives the guard a real baseline that survives the restart.
        """
        await super().async_added_to_hass()

        if self._key not in RESTORABLE_ENERGY_SENSORS:
            return

        last_data = await self.async_get_last_sensor_data()
        if last_data is None or not isinstance(last_data.native_value, (int, float)):
            return

        restored = float(last_data.native_value)
        current = self._coordinator.api.data.get(self._key)
        current_val = current if isinstance(current, (int, float)) else 0.0

        # Cumulative energy only increases: keep a genuine reading if the first poll
        # already captured one (device was not in warm-up), otherwise seed the baseline.
        if restored > current_val:
            self._coordinator.api.data[self._key] = restored
            log_debug(
                _LOGGER,
                "async_added_to_hass",
                "Restored lifetime energy baseline",
                sensor=self._key,
                restored=restored,
                poll_value=current_val,
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch new state data for the sensor."""
        self._state = self._coordinator.api.data[self._key]
        self.async_write_ha_state()
        # write debug log only on first sensor to avoid spamming the log
        if self._key == "potenza_prelevata":
            log_debug(
                _LOGGER,
                "_handle_coordinator_update",
                "Sensors state written to state machine",
            )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self) -> str | None:
        """Return the sensor icon."""
        return self._icon

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the sensor device_class."""
        return self._device_class

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return the sensor state_class."""
        return self._state_class

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the sensor entity_category."""
        if self._state_class is None:
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self._key in self._coordinator.api.data:
            return self._coordinator.api.data[self._key]
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
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}_{self._device_sn}_{self._key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            configuration_url=f"http://{self._device_host}",
            identifiers={(DOMAIN, self._device_sn)},
            manufacturer=self._device_manufact,
            model=self._device_model,
            name=self._device_name,
            serial_number=self._device_sn,
        )
