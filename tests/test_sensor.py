"""Tests for Sinapsi Alfa sensor platform."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.sinapsi_alfa.const import CONF_NAME, DOMAIN, SENSOR_ENTITIES
from custom_components.sinapsi_alfa.sensor import SinapsiAlfaSensor, async_setup_entry
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

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

        result = await async_setup_entry(hass, mock_config_entry_with_runtime, async_add_entities)

        assert result is True
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


class TestSensorEntityDefinitions:
    """Tests for sensor entity definitions in const.py."""

    def test_sensor_entities_count(self):
        """Test correct number of sensor entities defined."""
        assert len(SENSOR_ENTITIES) == 24

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
