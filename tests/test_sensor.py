"""Tests for Sinapsi Alfa sensor platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sinapsi_alfa.const import CONF_NAME, DOMAIN, SENSOR_ENTITIES
from custom_components.sinapsi_alfa.sensor import SinapsiAlfaSensor, async_setup_entry
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorExtraStoredData,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .conftest import TEST_HOST, TEST_MAC, TEST_NAME


@pytest.fixture
def mock_coordinator(mock_api_data):
    """Create mock coordinator."""
    coordinator = MagicMock()
    coordinator.api = MagicMock()
    coordinator.api.data = mock_api_data
    coordinator.api.name = TEST_NAME
    coordinator.api.host = TEST_HOST
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_config_entry_with_runtime():
    """Create mock config entry with runtime data."""
    entry = MagicMock()
    entry.data = {CONF_NAME: TEST_NAME}
    return entry


class TestAsyncSetupEntry:
    """Tests for sensor async_setup_entry."""

    async def test_setup_entry_creates_sensors(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_runtime,
        mock_coordinator,
    ):
        """Test setup creates sensor entities."""
        mock_config_entry_with_runtime.runtime_data = MagicMock()
        mock_config_entry_with_runtime.runtime_data.coordinator = mock_coordinator
        async_add_entities = MagicMock()

        # Platform setup functions return None (not bool)
        await async_setup_entry(hass, mock_config_entry_with_runtime, async_add_entities)

        async_add_entities.assert_called_once()
        # Check that sensors were created
        sensors = async_add_entities.call_args[0][0]
        assert len(sensors) > 0
        assert all(isinstance(s, SinapsiAlfaSensor) for s in sensors)

    async def test_setup_entry_skips_none_values(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_runtime,
        mock_coordinator,
    ):
        """Test setup skips sensors with None values."""
        # Set some sensor values to None
        mock_coordinator.api.data["potenza_prelevata"] = None
        mock_config_entry_with_runtime.runtime_data = MagicMock()
        mock_config_entry_with_runtime.runtime_data.coordinator = mock_coordinator
        async_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry_with_runtime, async_add_entities)

        sensors = async_add_entities.call_args[0][0]
        sensor_keys = [s._key for s in sensors]
        # potenza_prelevata should not be in the list
        assert "potenza_prelevata" not in sensor_keys

    async def test_setup_entry_skips_missing_keys(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_runtime,
        mock_coordinator,
    ):
        """Test setup skips sensors whose key is absent from api.data.

        Regression: the production validity gate withholds the calculated energy
        sensors from api.data until the device reports valid production data.
        Direct dict subscripting raised KeyError and crashed the whole sensor
        platform setup (issue #217, v1.13.8).
        """
        del mock_coordinator.api.data["energia_consumata"]
        del mock_coordinator.api.data["energia_auto_consumata"]
        mock_config_entry_with_runtime.runtime_data = MagicMock()
        mock_config_entry_with_runtime.runtime_data.coordinator = mock_coordinator
        async_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry_with_runtime, async_add_entities)

        sensors = async_add_entities.call_args[0][0]
        sensor_keys = [s._key for s in sensors]
        assert "energia_consumata" not in sensor_keys
        assert "energia_auto_consumata" not in sensor_keys
        # The rest of the platform must still be created
        assert len(sensors) > 0


class TestSinapsiAlfaSensor:
    """Tests for SinapsiAlfaSensor class."""

    @pytest.fixture
    def power_sensor(self, mock_coordinator):
        """Create a power sensor."""
        return SinapsiAlfaSensor(
            coordinator=mock_coordinator,
            name="Potenza Prelevata",
            key="potenza_prelevata",
            icon="mdi:transmission-tower-export",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfPower.KILO_WATT,
        )

    @pytest.fixture
    def energy_sensor(self, mock_coordinator):
        """Create an energy sensor."""
        return SinapsiAlfaSensor(
            coordinator=mock_coordinator,
            name="Energia Prelevata",
            key="energia_prelevata",
            icon="mdi:transmission-tower-export",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
        )

    @pytest.fixture
    def diagnostic_sensor(self, mock_coordinator):
        """Create a diagnostic sensor (no state_class)."""
        return SinapsiAlfaSensor(
            coordinator=mock_coordinator,
            name="Fascia Oraria Attuale",
            key="fascia_oraria_attuale",
            icon="mdi:information-outline",
            device_class=None,
            state_class=None,
            unit=None,
        )

    def test_sensor_init(self, power_sensor, mock_coordinator):
        """Test sensor initialization."""
        assert power_sensor._key == "potenza_prelevata"
        assert power_sensor._icon == "mdi:transmission-tower-export"
        assert power_sensor._device_class == SensorDeviceClass.POWER
        assert power_sensor._state_class == SensorStateClass.MEASUREMENT
        assert power_sensor._unit_of_measurement == UnitOfPower.KILO_WATT
        assert power_sensor._attr_translation_key == "potenza_prelevata"
        assert power_sensor._attr_has_entity_name is True

    def test_power_sensor_has_3_decimal_display_precision(self, power_sensor):
        """Power sensors must display 3 decimals (1 W resolution in kW)."""
        assert power_sensor._attr_suggested_display_precision == 3

    def test_energy_sensor_uses_ha_default_display_precision(self, energy_sensor):
        """Energy sensors intentionally keep HA's 2-decimal default for kWh."""
        assert not hasattr(energy_sensor, "_attr_suggested_display_precision") or (
            energy_sensor._attr_suggested_display_precision is None
        )

    def test_diagnostic_sensor_has_no_display_precision(self, diagnostic_sensor):
        """Non-power/energy sensors must not set a display precision override."""
        assert not hasattr(diagnostic_sensor, "_attr_suggested_display_precision") or (
            diagnostic_sensor._attr_suggested_display_precision is None
        )

    def test_native_unit_of_measurement(self, power_sensor):
        """Test native_unit_of_measurement property."""
        assert power_sensor.native_unit_of_measurement == UnitOfPower.KILO_WATT

    def test_icon(self, power_sensor):
        """Test icon property."""
        assert power_sensor.icon == "mdi:transmission-tower-export"

    def test_device_class(self, power_sensor):
        """Test device_class property."""
        assert power_sensor.device_class == SensorDeviceClass.POWER

    def test_state_class(self, power_sensor):
        """Test state_class property."""
        assert power_sensor.state_class == SensorStateClass.MEASUREMENT

    def test_entity_category_none_for_measurement(self, power_sensor):
        """Test entity_category is None for measurement sensors."""
        assert power_sensor.entity_category is None

    def test_entity_category_diagnostic_when_no_state_class(self, diagnostic_sensor):
        """Test entity_category is DIAGNOSTIC when no state_class."""
        assert diagnostic_sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_native_value(self, power_sensor):
        """Test native_value returns data from coordinator."""
        assert power_sensor.native_value == 1.5  # From mock_api_data

    def test_native_value_none_when_missing(self, power_sensor):
        """Test native_value returns None when key missing."""
        del power_sensor._coordinator.api.data["potenza_prelevata"]
        assert power_sensor.native_value is None

    def test_state_attributes(self, power_sensor):
        """Test state_attributes returns None."""
        assert power_sensor.state_attributes is None

    def test_should_poll(self, power_sensor):
        """Test should_poll returns False."""
        assert power_sensor.should_poll is False

    def test_available(self, power_sensor):
        """Test available property."""
        assert power_sensor.available is True

    def test_available_false_when_update_failed(self, power_sensor):
        """Test available is False when update failed."""
        power_sensor.coordinator.last_update_success = False
        assert power_sensor.available is False

    def test_unique_id(self, power_sensor):
        """Test unique_id format."""
        expected = f"{DOMAIN}_{TEST_MAC}_potenza_prelevata"
        assert power_sensor.unique_id == expected

    def test_device_info(self, power_sensor):
        """Test device_info returns correct dict."""
        info = power_sensor.device_info
        assert info["manufacturer"] == "Sinapsi"
        assert info["model"] == "Alfa"
        assert info["name"] == TEST_NAME
        assert info["serial_number"] == TEST_MAC
        assert (DOMAIN, TEST_MAC) in info["identifiers"]
        assert info["configuration_url"] == f"http://{TEST_HOST}"

    def test_handle_coordinator_update(self, power_sensor):
        """Test _handle_coordinator_update callback."""
        with patch.object(power_sensor, "async_write_ha_state") as mock_write:
            power_sensor._handle_coordinator_update()
            mock_write.assert_called_once()
            assert power_sensor._state == 1.5

    def test_handle_coordinator_update_logs_for_first_sensor(self, power_sensor):
        """Test debug log is written for first sensor (potenza_prelevata)."""
        with (
            patch.object(power_sensor, "async_write_ha_state"),
            patch("custom_components.sinapsi_alfa.sensor.log_debug") as mock_log,
        ):
            power_sensor._handle_coordinator_update()
            # Should log because key is potenza_prelevata
            mock_log.assert_called()

    def test_handle_coordinator_update_no_log_for_other_sensors(self, diagnostic_sensor):
        """Test debug log is NOT written for other sensors."""
        with (
            patch.object(diagnostic_sensor, "async_write_ha_state"),
            patch("custom_components.sinapsi_alfa.sensor.log_debug") as mock_log,
        ):
            diagnostic_sensor._handle_coordinator_update()
            # Should not log because key is not potenza_prelevata
            mock_log.assert_not_called()


def _energy_sensor(coordinator, key, sensor_scope="lifetime"):
    """Build a TOTAL_INCREASING energy sensor with the given scope."""
    return SinapsiAlfaSensor(
        coordinator=coordinator,
        name=key.replace("_", " ").title(),
        key=key,
        icon="mdi:flash",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        sensor_scope=sensor_scope,
    )


class TestSinapsiAlfaSensorRestore:
    """Tests for cold-restart baseline recovery via RestoreSensor (issue #206).

    After an HA restart the device returns 0 on its energy registers during a ~100s
    warm-up. async_added_to_hass keeps the last persisted value on the instance as a
    baseline for the native_value stale-value guards.
    """

    async def _added_to_hass(self, sensor, restored_value):
        """Run async_added_to_hass with the coordinator base call stubbed.

        Pass the sentinel "_NONE_" for no restore data (fresh install).
        """
        last_data = (
            None
            if restored_value == "_NONE_"
            else SensorExtraStoredData(restored_value, UnitOfEnergy.KILO_WATT_HOUR)
        )
        sensor.async_get_last_sensor_data = AsyncMock(return_value=last_data)
        with patch.object(CoordinatorEntity, "async_added_to_hass", AsyncMock()):
            await sensor.async_added_to_hass()
        return sensor.async_get_last_sensor_data

    async def test_restore_stores_baseline_on_instance(self, mock_coordinator):
        """A restored value is kept on the instance, not seeded into api.data."""
        mock_coordinator.api.data["energia_prelevata"] = 0.0
        sensor = _energy_sensor(mock_coordinator, "energia_prelevata")

        await self._added_to_hass(sensor, 7737.839)

        assert sensor._restored_native_value == 7737.839
        # api.data is left untouched — the guard is decoupled from the coordinator.
        assert mock_coordinator.api.data["energia_prelevata"] == 0.0

    async def test_restore_no_data_leaves_baseline_none(self, mock_coordinator):
        """With no restore data (fresh install), the baseline stays None."""
        sensor = _energy_sensor(mock_coordinator, "energia_prelevata")

        await self._added_to_hass(sensor, "_NONE_")

        assert sensor._restored_native_value is None

    async def test_restore_ignores_non_numeric_value(self, mock_coordinator):
        """A non-numeric restored value is ignored."""
        sensor = _energy_sensor(mock_coordinator, "energia_prelevata")

        await self._added_to_hass(sensor, "unknown")

        assert sensor._restored_native_value is None

    async def test_restore_covers_daily_periodic_sensor(self, mock_coordinator):
        """Daily F1-F6 (periodic) sensors are accumulating and get a baseline."""
        sensor = _energy_sensor(
            mock_coordinator, "energia_prelevata_giornaliera_f1", sensor_scope="periodic"
        )

        await self._added_to_hass(sensor, 12.5)

        assert sensor._restored_native_value == 12.5

    async def test_non_accumulating_sensor_skips_restore(self, mock_coordinator):
        """Non-accumulating sensors return early without querying restore data."""
        sensor = SinapsiAlfaSensor(
            coordinator=mock_coordinator,
            name="Potenza Prelevata",
            key="potenza_prelevata",
            icon="mdi:transmission-tower-export",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfPower.KILO_WATT,
        )

        get_last = await self._added_to_hass(sensor, 999.0)

        get_last.assert_not_called()
        assert sensor._restored_native_value is None


class TestSinapsiAlfaSensorGuards:
    """Tests for the two native_value stale-value guards (issue #206)."""

    def _guard_sensor(
        self, coordinator, key, sensor_scope, api_value, restored=None, live_state=None
    ):
        """Build a TOTAL_INCREASING sensor wired for native_value guard tests.

        live_state=None → no live HA state (post-cold-restart). Otherwise a string
        state value. restored sets the cold-restart baseline.
        """
        sensor = _energy_sensor(coordinator, key, sensor_scope)
        sensor._restored_native_value = restored
        sensor.entity_id = f"sensor.{key}"
        coordinator.api.data[key] = api_value
        hass = MagicMock()
        if live_state is None:
            hass.states.get.return_value = None
        else:
            state = MagicMock()
            state.state = live_state
            hass.states.get.return_value = state
        sensor.hass = hass
        return sensor

    def test_guard1_holds_last_value_over_decreased_lifetime_value(self, mock_coordinator):
        """Guard 1: a lifetime value below the live state is replaced by the live state.

        Returning the live state (instead of None) keeps the entity numeric: an
        "unknown" gap would disable Guard 1 on the next poll and let RestoreSensor
        snapshot a non-numeric baseline (2026-07-22 incident).
        """
        sensor = self._guard_sensor(
            mock_coordinator, "energia_prelevata", "lifetime", 50.0, live_state="100.0"
        )
        assert sensor.native_value == 100.0

    def test_guard1_holds_over_float_artifact_decrease(self, mock_coordinator):
        """Guard 1: a float-artifact hair below the stored state is held, not published.

        The recorder treats ANY decrease of a TOTAL_INCREASING state as a meter
        reset, so even a 4e-12 artifact must never reach the state machine.
        """
        sensor = self._guard_sensor(
            mock_coordinator,
            "energia_prelevata",
            "lifetime",
            38479.123999999996,
            live_state="38479.124",
        )
        assert sensor.native_value == 38479.124

    def test_guard1_allows_equal_lifetime_value(self, mock_coordinator):
        """Guard 1: a value equal to the live state passes."""
        sensor = self._guard_sensor(
            mock_coordinator, "energia_prelevata", "lifetime", 100.0, live_state="100.0"
        )
        assert sensor.native_value == 100.0

    def test_guard1_allows_increased_lifetime_value(self, mock_coordinator):
        """Guard 1: a value above the live state passes."""
        sensor = self._guard_sensor(
            mock_coordinator, "energia_prelevata", "lifetime", 150.0, live_state="100.0"
        )
        assert sensor.native_value == 150.0

    def test_guard1_allows_when_live_state_non_numeric(self, mock_coordinator):
        """Guard 1: a non-numeric live state is ignored, value passes through."""
        sensor = self._guard_sensor(
            mock_coordinator, "energia_prelevata", "lifetime", 50.0, live_state="garbage"
        )
        assert sensor.native_value == 50.0

    def test_guard1_skipped_for_periodic_sensor(self, mock_coordinator):
        """Guard 1 excludes daily sensors: the midnight reset to 0 passes through."""
        sensor = self._guard_sensor(
            mock_coordinator,
            "energia_prelevata_giornaliera_f1",
            "periodic",
            0.0,
            live_state="23.4",
        )
        assert sensor.native_value == 0.0

    def test_guard2_blocks_warmup_zero_after_restart(self, mock_coordinator):
        """Guard 2: a warm-up 0 below the restored baseline is discarded."""
        sensor = self._guard_sensor(
            mock_coordinator, "energia_prelevata", "lifetime", 0.0, restored=7737.839
        )
        assert sensor.native_value is None

    def test_guard2_allows_value_above_baseline(self, mock_coordinator):
        """Guard 2: a value above the restored baseline passes."""
        sensor = self._guard_sensor(
            mock_coordinator, "energia_prelevata", "lifetime", 7800.0, restored=7737.839
        )
        assert sensor.native_value == 7800.0

    def test_guard2_allows_value_equal_to_baseline(self, mock_coordinator):
        """Guard 2: a value equal to the restored baseline passes."""
        sensor = self._guard_sensor(
            mock_coordinator, "energia_prelevata", "lifetime", 7737.839, restored=7737.839
        )
        assert sensor.native_value == 7737.839

    def test_guard2_protects_periodic_sensor_after_restart(self, mock_coordinator):
        """Guard 2 covers daily sensors: a warm-up 0 after restart is discarded."""
        sensor = self._guard_sensor(
            mock_coordinator,
            "energia_immessa_giornaliera_f1",
            "periodic",
            0.0,
            restored=12.5,
        )
        assert sensor.native_value is None

    def test_guard2_inert_without_restore_data(self, mock_coordinator):
        """Guard 2: with no restored baseline (fresh install) the value passes."""
        sensor = self._guard_sensor(
            mock_coordinator, "energia_prelevata", "lifetime", 0.0, restored=None
        )
        assert sensor.native_value == 0.0

    def test_live_state_takes_priority_over_restored_baseline(self, mock_coordinator):
        """With a live state, Guard 1 runs and Guard 2 (restored baseline) is bypassed."""
        # value 70 is above the restored baseline (50) but below the live state (100):
        # Guard 1 wins and holds the live state value.
        sensor = self._guard_sensor(
            mock_coordinator,
            "energia_prelevata",
            "lifetime",
            70.0,
            restored=50.0,
            live_state="100.0",
        )
        assert sensor.native_value == 100.0

    def test_non_accumulating_sensor_skips_guards(self, mock_coordinator):
        """A power (MEASUREMENT) sensor bypasses both guards entirely."""
        sensor = SinapsiAlfaSensor(
            coordinator=mock_coordinator,
            name="Potenza Prelevata",
            key="potenza_prelevata",
            icon="mdi:transmission-tower-export",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfPower.KILO_WATT,
        )
        sensor.hass = MagicMock()
        mock_coordinator.api.data["potenza_prelevata"] = 1.5

        assert sensor.native_value == 1.5
        sensor.hass.states.get.assert_not_called()


class TestSensorEntityDefinitions:
    """Tests for sensor entity definitions in const.py."""

    def test_sensor_entities_count(self):
        """Test correct number of sensor entities defined."""
        assert len(SENSOR_ENTITIES) == 27

    def test_all_sensors_have_required_fields(self):
        """Test all sensors have required fields."""
        required_fields = ["name", "key", "icon", "device_class", "state_class", "unit"]
        for sensor in SENSOR_ENTITIES:
            for field in required_fields:
                assert field in sensor, f"Sensor {sensor.get('key')} missing {field}"

    def test_calculated_sensors_have_no_modbus_addr(self):
        """Test calculated sensors have None modbus_addr."""
        calculated = [
            "potenza_consumata",
            "potenza_auto_consumata",
            "energia_consumata",
            "energia_auto_consumata",
        ]
        for sensor in SENSOR_ENTITIES:
            if sensor["key"] in calculated:
                assert sensor["modbus_type"] == "calcolato"
                assert sensor["modbus_addr"] is None

    def test_energy_sensors_have_sensor_scope(self):
        """All 17 TOTAL_INCREASING energy sensors are tagged lifetime or periodic."""
        lifetime = {s["key"] for s in SENSOR_ENTITIES if s.get("sensor_scope") == "lifetime"}
        periodic = {s["key"] for s in SENSOR_ENTITIES if s.get("sensor_scope") == "periodic"}
        total_increasing = {
            s["key"]
            for s in SENSOR_ENTITIES
            if s["state_class"] == SensorStateClass.TOTAL_INCREASING
        }

        assert lifetime == {
            "energia_prelevata",
            "energia_immessa",
            "energia_prodotta",
            "energia_consumata",
            "energia_auto_consumata",
        }
        assert len(periodic) == 12
        # Every TOTAL_INCREASING sensor is tagged, and only those.
        assert lifetime | periodic == total_increasing
