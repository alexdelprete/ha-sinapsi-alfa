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
from .const import CONF_NAME, DOMAIN, SENSOR_ENTITIES
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
                    sensor_def.get("sensor_scope"),
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
        sensor_scope: str | None = None,
    ) -> None:
        """Class Initializitation."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._key = key
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._unit_of_measurement = unit
        # Cold-restart / stale-value guard flags (issue #206).
        # Accumulating = any TOTAL_INCREASING energy sensor (all 17). Lifetime = the
        # 5 never-resetting totals (raw + calculated), tagged sensor_scope="lifetime"
        # in const.py; daily F1-F6 sensors are "periodic" — accumulating, not lifetime.
        self._is_accumulating_sensor = state_class == SensorStateClass.TOTAL_INCREASING
        self._is_lifetime_sensor = sensor_scope == "lifetime"
        # Restored baseline for the cold-restart guard; set in async_added_to_hass.
        self._restored_native_value: float | None = None
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
        """Restore the last known value as a cold-restart baseline (issue #206).

        After a Home Assistant restart the device returns 0 (or stale low values) on
        its energy registers during a ~100s warm-up window. HA's TOTAL_INCREASING
        statistics would read a published 0 as a meter reset and double-count. For
        every accumulating (TOTAL_INCREASING) sensor, the last value persisted by
        RestoreSensor is kept on the instance and used by the stale-value guard in
        native_value as a baseline until the first real value is published.
        """
        await super().async_added_to_hass()

        if not self._is_accumulating_sensor:
            return

        last_data = await self.async_get_last_sensor_data()
        if last_data is None or not isinstance(last_data.native_value, (int, float)):
            return

        self._restored_native_value = float(last_data.native_value)
        log_debug(
            _LOGGER,
            "async_added_to_hass",
            "Restored accumulating-sensor baseline",
            sensor=self._key,
            restored=self._restored_native_value,
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
        """Return the state of the sensor, guarding accumulating sensors.

        Two independent guards protect TOTAL_INCREASING energy sensors from being
        published with a decreased value (issue #206), which HA would treat as a
        meter reset and double-count:

        - Guard 1 (lifetime sensors, normal operation): when a live HA state exists,
          a value below it is discarded. Daily F1-F6 sensors are excluded so their
          legitimate midnight reset is allowed through.
        - Guard 2 (all accumulating sensors, post-cold-restart): while no live state
          exists yet, a value below the restored baseline is discarded — covering the
          device warm-up window after an HA restart.
        """
        if self._key not in self._coordinator.api.data:
            return None
        value = self._coordinator.api.data[self._key]

        if (self._is_lifetime_sensor or self._is_accumulating_sensor) and isinstance(
            value, (int, float)
        ):
            current_state = self.hass.states.get(self.entity_id)
            has_live_state = current_state is not None and current_state.state not in (
                "unknown",
                "unavailable",
                None,
            )

            # Guard 1: lifetime sensors must never decrease during normal operation.
            if self._is_lifetime_sensor and has_live_state:
                try:
                    if value < float(current_state.state):
                        log_debug(
                            _LOGGER,
                            "native_value",
                            "Discarding decreased lifetime value",
                            sensor=self._key,
                            value=value,
                            current=current_state.state,
                        )
                        return None
                except ValueError, TypeError:
                    pass  # Current state not numeric — allow through.

            # Guard 2: after a cold restart, block values below the restored baseline.
            if (
                self._is_accumulating_sensor
                and not has_live_state
                and self._restored_native_value is not None
                and value < self._restored_native_value
            ):
                log_debug(
                    _LOGGER,
                    "native_value",
                    "Discarding warm-up value below restored baseline",
                    sensor=self._key,
                    value=value,
                    baseline=self._restored_native_value,
                )
                return None

        return value

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
