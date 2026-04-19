"""Tests for Sinapsi Alfa API."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

from modbuslink import (
    ConnectError as ModbusConnectionError,
    CrcError,
    InvalidReplyError,
    ModbusException,
    ModbusLinkError,
    TimeOutError as ModbusTimeoutError,
)
import pytest

from custom_components.sinapsi_alfa import api as api_module
from custom_components.sinapsi_alfa.api import (
    BATCH_MAX_RETRIES,
    MAX_PROTOCOL_ERRORS_PER_CYCLE,
    SENSOR_MAP,
    SinapsiAlfaAPI,
    SinapsiConnectionError,
    SinapsiModbusError,
    _build_sensor_map,
)
from custom_components.sinapsi_alfa.const import (
    CUMULATIVE_ENERGY_SENSORS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    MANUFACTURER,
    MAX_EVENT_VALUE,
    MODEL,
    REGISTER_BATCHES,
    SENSOR_ENTITIES,
    SYNC_TIMEOUT_SECONDS,
)

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT


@pytest.fixture
def mock_hass():
    """Create mock HomeAssistant instance."""
    return MagicMock()


@pytest.fixture
def mock_transport():
    """Create mock AsyncTcpTransport."""
    with patch(
        "custom_components.sinapsi_alfa.api.AsyncTcpTransport",
        autospec=True,
    ) as mock_transport_class:
        mock_transport = mock_transport_class.return_value
        mock_transport.open = AsyncMock()
        mock_transport.close = AsyncMock()
        yield mock_transport


@pytest.fixture
def mock_client():
    """Create mock AsyncModbusClient."""
    with patch(
        "custom_components.sinapsi_alfa.api.AsyncModbusClient",
        autospec=True,
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        # Default: successful read returning sample data
        mock_client.read_holding_registers = AsyncMock(return_value=[0] * 40)
        yield mock_client


class TestSinapsiAlfaAPI:
    """Tests for SinapsiAlfaAPI class."""

    def test_api_init(self, mock_hass, mock_transport, mock_client):
        """Test API initialization."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
            skip_mac_detection=False,
        )

        assert api.name == TEST_NAME
        assert api.host == TEST_HOST
        assert api._port == TEST_PORT
        assert api._timeout == DEFAULT_TIMEOUT
        assert api._skip_mac_detection is False

    def test_api_init_with_skip_mac(self, mock_hass, mock_transport, mock_client):
        """Test API initialization with MAC detection skipped."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
            skip_mac_detection=True,
        )

        assert api._skip_mac_detection is True

    def test_api_init_invalid_port(self, mock_hass, mock_transport, mock_client):
        """Test API initialization with invalid port."""
        with pytest.raises(ValueError, match=r"Port .* is out of valid range"):
            SinapsiAlfaAPI(
                mock_hass,
                TEST_NAME,
                TEST_HOST,
                70000,  # Invalid port
                DEFAULT_SCAN_INTERVAL,
                DEFAULT_TIMEOUT,
            )

    def test_api_init_data_structure(self, mock_hass, mock_transport, mock_client):
        """Test that data structure is initialized properly."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Check metadata
        assert api.data["manufact"] == MANUFACTURER
        assert api.data["model"] == MODEL
        assert api.data["sn"] == ""

        # Check some sensor default values
        assert api.data["potenza_prelevata"] == 0.0
        assert api.data["energia_prelevata"] == 0.0

    def test_properties(self, mock_hass, mock_transport, mock_client):
        """Test API properties."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        assert api.name == TEST_NAME
        assert api.host == TEST_HOST
        assert api.uid == ""  # Not set until first data fetch

    async def test_close(self, mock_hass, mock_transport, mock_client):
        """Test API close method."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        await api.close()

        mock_transport.close.assert_called_once()
        assert api._connection_healthy is False


class TestSinapsiConnectionError:
    """Tests for SinapsiConnectionError exception."""

    def test_connection_error_basic(self):
        """Test basic connection error."""
        error = SinapsiConnectionError("Connection failed")

        assert str(error) == "Connection failed"
        assert error.host is None
        assert error.port is None

    def test_connection_error_with_details(self):
        """Test connection error with host/port details."""
        error = SinapsiConnectionError("Connection timeout", host=TEST_HOST, port=TEST_PORT)

        assert str(error) == "Connection timeout"
        assert error.host == TEST_HOST
        assert error.port == TEST_PORT


class TestSinapsiModbusError:
    """Tests for SinapsiModbusError exception."""

    def test_modbus_error_basic(self):
        """Test basic Modbus error."""
        error = SinapsiModbusError("Read failed")

        assert str(error) == "Read failed"
        assert error.address is None
        assert error.operation is None

    def test_modbus_error_with_details(self):
        """Test Modbus error with address/operation details."""
        error = SinapsiModbusError("Register read failed", address=100, operation="read_holding")

        assert str(error) == "Register read failed"
        assert error.address == 100
        assert error.operation == "read_holding"


class TestDataExtraction:
    """Tests for data extraction methods."""

    def test_extract_uint16(self, mock_hass, mock_transport, mock_client):
        """Test uint16 extraction."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        registers = [100, 200, 300]
        assert api._extract_uint16(registers, 0) == 100
        assert api._extract_uint16(registers, 1) == 200
        assert api._extract_uint16(registers, 2) == 300

    def test_extract_uint32(self, mock_hass, mock_transport, mock_client):
        """Test uint32 extraction (big-endian)."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # High word = 1, Low word = 2 -> (1 << 16) | 2 = 65538
        registers = [1, 2]
        assert api._extract_uint32(registers, 0) == 65538

        # High word = 0x0001, Low word = 0xFFFF -> 0x0001FFFF = 131071
        registers = [1, 65535]
        assert api._extract_uint32(registers, 0) == 131071


class TestSpecialValueHandling:
    """Tests for special value handling."""

    def test_invalid_distacco_value(self, mock_hass, mock_transport, mock_client):
        """Test handling of invalid disconnect timer value."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # INVALID_DISTACCO_VALUE (65535) should return 0
        result = api._apply_special_value_rules(65535, "tempo_residuo_distacco")
        assert result == 0

        # Normal value should pass through
        result = api._apply_special_value_rules(100, "tempo_residuo_distacco")
        assert result == 100

    def test_fascia_oraria_formatting(self, mock_hass, mock_transport, mock_client):
        """Test time band value formatting."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        assert api._apply_special_value_rules(1, "fascia_oraria_attuale") == "F1"
        assert api._apply_special_value_rules(3, "fascia_oraria_attuale") == "F3"
        assert api._apply_special_value_rules(6, "fascia_oraria_attuale") == "F6"


class TestDerivedValues:
    """Tests for calculated/derived values."""

    def test_calculate_derived_values(self, mock_hass, mock_transport, mock_client):
        """Test derived value calculations."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Set base values
        api.data["potenza_prelevata"] = 1.5
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0

        # Calculate derived values
        api._calculate_derived_values()

        # Verify calculations
        # potenza_auto_consumata = potenza_prodotta - potenza_immessa = 2.0 - 0.5 = 1.5
        assert api.data["potenza_auto_consumata"] == 1.5

        # potenza_consumata = potenza_auto_consumata + potenza_prelevata = 1.5 + 1.5 = 3.0
        assert api.data["potenza_consumata"] == 3.0

        # energia_auto_consumata = energia_prodotta - energia_immessa = 500 - 200 = 300
        assert api.data["energia_auto_consumata"] == 300.0

        # energia_consumata = energia_auto_consumata + energia_prelevata = 300 + 1000 = 1300
        assert api.data["energia_consumata"] == 1300.0

    def test_sync_guard_both_fresh(self, mock_hass, mock_transport, mock_client):
        """Test sync guard recalculates when both sensors update."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # First poll: initializes tracking
        api.data["potenza_prelevata"] = 0.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 0.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0

        # Both sensors update — should recalculate
        api.data["energia_prodotta"] = 501.0
        api.data["energia_immessa"] = 200.5
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.5

    def test_sync_guard_one_fresh_waits(self, mock_hass, mock_transport, mock_client):
        """Test sync guard holds when only one sensor updates."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # First poll
        api.data["potenza_prelevata"] = 0.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 0.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0

        # Only prodotta updates — should wait
        api.data["energia_prodotta"] = 501.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0  # Held
        assert api._first_unsync_time is not None

    def test_sync_guard_timeout_fires(self, mock_hass, mock_transport, mock_client):
        """Test sync guard timeout calculates after SYNC_TIMEOUT_SECONDS."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # First poll
        api.data["potenza_prelevata"] = 0.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 0.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api._calculate_derived_values()

        # Only prodotta updates — starts timer, should wait
        api.data["energia_prodotta"] = 501.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0  # Still held
        assert api._first_unsync_time is not None

        # Simulate time passing beyond timeout
        api._first_unsync_time = time.monotonic() - SYNC_TIMEOUT_SECONDS - 1

        # Next poll — timeout fires
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 301.0  # 501 - 200
        assert api._first_unsync_time is None

    def test_quiescent_reconciliation_fires(self, mock_hass, mock_transport, mock_client):
        """Test quiescent reconciliation aligns auto_consumata when sensors stabilize."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # First poll — initialize
        api.data["potenza_prelevata"] = 0.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 0.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0

        # Simulate a gap: manually set auto_consumata to a stale value
        # (as if the sync guard held it during a firmware update cycle)
        api.data["energia_auto_consumata"] = 299.0

        # Neither sensor changes — quiescent reconciliation should fire
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0  # Reconciled
        assert api._last_calc_prodotta == 500.0
        assert api._last_calc_immessa == 200.0

    def test_quiescent_reconciliation_noop_when_aligned(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test quiescent reconciliation is a no-op when values already match."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # First poll
        api.data["potenza_prelevata"] = 0.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 0.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0

        # Neither changes, already aligned — should stay at 300.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0

    def test_quiescent_reconciliation_tolerance(self, mock_hass, mock_transport, mock_client):
        """Test quiescent reconciliation ignores gaps smaller than tolerance."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # First poll
        api.data["potenza_prelevata"] = 0.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 0.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api._calculate_derived_values()

        # Set a tiny gap below tolerance (0.001)
        api.data["energia_auto_consumata"] = 300.0005

        # Neither changes — gap is below tolerance, should NOT reconcile
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0005  # Unchanged

    def test_consumata_always_updates(self, mock_hass, mock_transport, mock_client):
        """Test energia_consumata always reflects latest prelevata (beta.3 fix)."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # First poll
        api.data["potenza_prelevata"] = 0.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 0.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api._calculate_derived_values()
        assert api.data["energia_consumata"] == 1300.0  # 300 + 1000

        # Only prelevata changes (nighttime import), prodotta/immessa frozen
        api.data["energia_prelevata"] = 1001.0
        api._calculate_derived_values()
        assert api.data["energia_consumata"] == 1301.0  # 300 + 1001


class TestPortCheck:
    """Tests for port availability check."""

    async def test_check_port_success(self, mock_hass, mock_transport, mock_client):
        """Test successful port check."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        with patch("asyncio.open_connection") as mock_open:
            mock_writer = MagicMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()
            mock_open.return_value = (MagicMock(), mock_writer)

            result = await api.check_port()

            assert result is True
            mock_writer.close.assert_called_once()

    async def test_check_port_timeout(self, mock_hass, mock_transport, mock_client):
        """Test port check timeout."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        with patch("asyncio.open_connection", side_effect=TimeoutError):
            result = await api.check_port()

            assert result is False

    async def test_check_port_refused(self, mock_hass, mock_transport, mock_client):
        """Test port check connection refused."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError):
            result = await api.check_port()

            assert result is False


class TestAsyncGetData:
    """Tests for async_get_data method."""

    async def test_async_get_data_port_not_available(self, mock_hass, mock_transport, mock_client):
        """Test async_get_data when port is not available."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        with patch.object(api, "check_port", return_value=False):
            with pytest.raises(SinapsiConnectionError) as exc_info:
                await api.async_get_data()

            assert "Device not active" in str(exc_info.value)
            assert api._connection_healthy is False

    async def test_async_get_data_skip_mac_detection(self, mock_hass, mock_transport, mock_client):
        """Test async_get_data with MAC detection skipped."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
            skip_mac_detection=True,
        )

        # Return sample register data for all batch reads
        mock_client.read_holding_registers = AsyncMock(return_value=[0] * 40)

        with (
            patch.object(api, "check_port", return_value=True),
            patch.object(api, "read_modbus_alfa", return_value=True),
        ):
            await api.async_get_data()

        # Verify host-based ID was used
        expected_uid = f"{TEST_HOST.replace('.', '')}_{TEST_PORT}"
        assert api._uid == expected_uid
        assert api.data["sn"] == expected_uid

    async def test_async_get_data_with_mac_detection(self, mock_hass, mock_transport, mock_client):
        """Test async_get_data with MAC detection enabled."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
            skip_mac_detection=False,
        )

        with (
            patch.object(api, "check_port", return_value=True),
            patch.object(api, "get_mac_address", return_value="AABBCCDDEEFF"),
            patch.object(api, "read_modbus_alfa", return_value=True),
        ):
            result = await api.async_get_data()

        assert result is True
        assert api._uid == "AABBCCDDEEFF"
        assert api.data["sn"] == "AABBCCDDEEFF"
        assert api._connection_healthy is True

    async def test_async_get_data_modbus_connection_error(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test async_get_data handles ModbusConnectionError."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
            skip_mac_detection=True,
        )

        # Simulate connection error when entering client context
        mock_client.__aenter__ = AsyncMock(side_effect=ModbusConnectionError("Connection lost"))

        with (
            patch.object(api, "check_port", return_value=True),
            pytest.raises(SinapsiConnectionError) as exc_info,
        ):
            await api.async_get_data()

        assert "Connection failed" in str(exc_info.value)
        assert api._connection_healthy is False

    async def test_async_get_data_modbus_timeout_error(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test async_get_data handles ModbusTimeoutError."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
            skip_mac_detection=True,
        )

        mock_client.__aenter__ = AsyncMock(side_effect=ModbusTimeoutError("Timeout"))

        with (
            patch.object(api, "check_port", return_value=True),
            pytest.raises(SinapsiConnectionError) as exc_info,
        ):
            await api.async_get_data()

        assert "Connection failed" in str(exc_info.value)


class TestSensorMapBuilding:
    """Tests for sensor map building."""

    def test_build_sensor_map_returns_dict(self):
        """Test that _build_sensor_map returns a dictionary."""
        sensor_map = _build_sensor_map()
        assert isinstance(sensor_map, dict)

    def test_build_sensor_map_excludes_calculated(self):
        """Test that calculated sensors are excluded from map."""
        sensor_map = _build_sensor_map()
        # Calculated sensors should not be in the map
        assert "potenza_consumata" not in sensor_map
        assert "potenza_auto_consumata" not in sensor_map
        assert "energia_consumata" not in sensor_map
        assert "energia_auto_consumata" not in sensor_map

    def test_build_sensor_map_includes_modbus_sensors(self):
        """Test that modbus sensors are included in map."""
        sensor_map = _build_sensor_map()
        # Check some known modbus sensors
        assert "potenza_prelevata" in sensor_map
        assert "energia_prelevata" in sensor_map
        assert "fascia_oraria_attuale" in sensor_map

    def test_sensor_map_structure(self):
        """Test sensor map entry structure."""
        sensor_map = _build_sensor_map()
        # Each entry should be (batch_index, offset, modbus_type)
        for value in sensor_map.values():
            assert isinstance(value, tuple)
            assert len(value) == 3
            batch_idx, offset, modbus_type = value
            assert isinstance(batch_idx, int)
            assert isinstance(offset, int)
            assert modbus_type in ("uint16", "uint32")

    def test_sensor_map_global_constant(self):
        """Test that SENSOR_MAP constant is populated."""
        assert len(SENSOR_MAP) > 0
        # Should have all non-calculated sensors
        non_calc_count = sum(1 for s in SENSOR_ENTITIES if s["modbus_type"] != "calcolato")
        assert len(SENSOR_MAP) == non_calc_count


class TestFlushBuffer:
    """Tests for buffer flush functionality."""

    async def test_flush_buffer_success(self, mock_hass, mock_transport, mock_client):
        """Test successful buffer flush."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        mock_transport.flush = AsyncMock(return_value=42)

        result = await api._flush_buffer()

        assert result == 42
        mock_transport.flush.assert_called_once()

    async def test_flush_buffer_zero_bytes(self, mock_hass, mock_transport, mock_client):
        """Test buffer flush with no data to flush."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        mock_transport.flush = AsyncMock(return_value=0)

        result = await api._flush_buffer()

        assert result == 0

    async def test_flush_buffer_oserror_returns_zero(self, mock_hass, mock_transport, mock_client):
        """Test buffer flush returns 0 on OSError."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        mock_transport.flush = AsyncMock(side_effect=OSError("Socket error"))

        result = await api._flush_buffer()

        assert result == 0


class TestConnectionReset:
    """Tests for connection reset functionality."""

    async def test_reset_connection_success(self, mock_hass, mock_transport, mock_client):
        """Test successful connection reset."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        mock_transport.open = AsyncMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await api._reset_connection()

        mock_transport.close.assert_called()
        mock_transport.open.assert_called_once()

    async def test_reset_connection_reconnect_fails(self, mock_hass, mock_transport, mock_client):
        """Test connection reset when reconnect fails."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        mock_transport.open = AsyncMock(side_effect=OSError("Connection refused"))

        with patch("asyncio.sleep", new_callable=AsyncMock), pytest.raises(OSError):
            await api._reset_connection()


class TestGetMacAddress:
    """Tests for MAC address retrieval."""

    async def test_get_mac_address_success_first_attempt(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test successful MAC retrieval on first attempt."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        with (
            patch.object(api, "check_port", return_value=True),
            patch("custom_components.sinapsi_alfa.api.getmac") as mock_getmac,
        ):
            mock_getmac.get_mac_address.return_value = "aa:bb:cc:dd:ee:ff"
            result = await api.get_mac_address()

        assert result == "AABBCCDDEEFF"

    async def test_get_mac_address_retry_success(self, mock_hass, mock_transport, mock_client):
        """Test MAC retrieval succeeds after retry."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        with (
            patch.object(api, "check_port", return_value=True),
            patch("custom_components.sinapsi_alfa.api.getmac") as mock_getmac,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            # Fail first two attempts, succeed on third
            mock_getmac.get_mac_address.side_effect = [None, None, "aa:bb:cc:dd:ee:ff"]
            result = await api.get_mac_address()

        assert result == "AABBCCDDEEFF"

    async def test_get_mac_address_fallback_to_host_id(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test fallback to host-based ID when MAC not found."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        with (
            patch.object(api, "check_port", return_value=True),
            patch("custom_components.sinapsi_alfa.api.getmac") as mock_getmac,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_getmac.get_mac_address.return_value = None
            result = await api.get_mac_address()

        expected = f"{TEST_HOST.replace('.', '')}_{TEST_PORT}"
        assert result == expected

    async def test_get_mac_address_oserror_retry(self, mock_hass, mock_transport, mock_client):
        """Test MAC retrieval retries on OSError."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        with (
            patch.object(api, "check_port", return_value=True),
            patch("custom_components.sinapsi_alfa.api.getmac") as mock_getmac,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            # OSError then success
            mock_getmac.get_mac_address.side_effect = [
                OSError("Network error"),
                "aa:bb:cc:dd:ee:ff",
            ]
            result = await api.get_mac_address()

        assert result == "AABBCCDDEEFF"


class TestReadBatch:
    """Tests for batch reading functionality."""

    async def test_read_batch_success(self, mock_hass, mock_transport, mock_client):
        """Test successful batch read."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        expected_data = [100, 200, 300, 400, 500]
        mock_client.read_holding_registers = AsyncMock(return_value=expected_data)

        result = await api._read_batch(2, 5)

        assert result == expected_data

    async def test_read_batch_connection_error_retries(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read retries on connection error."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        expected_data = [100, 200, 300]
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[
                ModbusConnectionError("Connection lost"),
                ModbusConnectionError("Connection lost"),
                expected_data,
            ]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await api._read_batch(2, 3)

        assert result == expected_data
        assert mock_client.read_holding_registers.call_count == 3

    async def test_read_batch_connection_error_exhausted(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read fails after all retries exhausted."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        mock_client.read_holding_registers = AsyncMock(
            side_effect=ModbusConnectionError("Connection lost")
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(SinapsiConnectionError) as exc_info,
        ):
            await api._read_batch(2, 3)

        assert f"Batch read failed after {BATCH_MAX_RETRIES} attempts" in str(exc_info.value)
        assert api._connection_healthy is False

    async def test_read_batch_timeout_error_retries(self, mock_hass, mock_transport, mock_client):
        """Test batch read retries on timeout error with flush."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        expected_data = [100, 200]
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[
                ModbusTimeoutError("Timeout"),
                expected_data,
            ]
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch.object(api, "_flush_buffer", new_callable=AsyncMock) as mock_flush,
        ):
            result = await api._read_batch(2, 2)

        assert result == expected_data
        # Flush should be called after timeout
        mock_flush.assert_called_once()

    async def test_read_batch_invalid_response_flushes_buffer(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read flushes buffer on InvalidReplyError."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        expected_data = [100]
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[
                InvalidReplyError("Transaction ID mismatch"),
                expected_data,
            ]
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch.object(api, "_flush_buffer", new_callable=AsyncMock) as mock_flush,
            patch.object(api, "_reset_connection", new_callable=AsyncMock) as mock_reset,
        ):
            result = await api._read_batch(2, 1)

        assert result == expected_data
        # Flush should be called first
        mock_flush.assert_called_once()
        # Reset should NOT be called (below error threshold)
        mock_reset.assert_not_called()
        assert api._protocol_errors_this_cycle == 1

    async def test_read_batch_crc_error_flushes_buffer(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read flushes buffer on CrcError."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        expected_data = [100]
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[
                CrcError("CRC mismatch"),
                expected_data,
            ]
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch.object(api, "_flush_buffer", new_callable=AsyncMock) as mock_flush,
            patch.object(api, "_reset_connection", new_callable=AsyncMock) as mock_reset,
        ):
            result = await api._read_batch(2, 1)

        assert result == expected_data
        # Flush should be called first
        mock_flush.assert_called_once()
        # Reset should NOT be called (below error threshold)
        mock_reset.assert_not_called()

    async def test_read_batch_resets_connection_at_error_threshold(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read resets connection when protocol errors hit threshold."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Set protocol errors just below threshold so next error triggers reset
        api._protocol_errors_this_cycle = MAX_PROTOCOL_ERRORS_PER_CYCLE - 1

        expected_data = [100]
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[
                InvalidReplyError("Transaction ID mismatch"),
                expected_data,
            ]
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch.object(api, "_flush_buffer", new_callable=AsyncMock) as mock_flush,
            patch.object(api, "_reset_connection", new_callable=AsyncMock) as mock_reset,
        ):
            result = await api._read_batch(2, 1)

        assert result == expected_data
        # Flush should be called
        mock_flush.assert_called_once()
        # Reset SHOULD be called (at error threshold)
        mock_reset.assert_called_once()
        assert api._protocol_errors_this_cycle == MAX_PROTOCOL_ERRORS_PER_CYCLE

    async def test_read_batch_modbus_exception_fails_immediately(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read fails immediately on ModbusException."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # ModbusException requires exception_code and function_code arguments
        mock_client.read_holding_registers = AsyncMock(
            side_effect=ModbusException(exception_code=0x01, function_code=0x03)
        )

        with pytest.raises(SinapsiModbusError) as exc_info:
            await api._read_batch(2, 1)

        assert "Modbus error at address 2" in str(exc_info.value)
        # Should fail immediately, not retry
        assert mock_client.read_holding_registers.call_count == 1

    async def test_read_batch_modbuslink_error_fails_immediately(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read fails immediately on generic ModbusLinkError."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        mock_client.read_holding_registers = AsyncMock(side_effect=ModbusLinkError("Unknown error"))

        with pytest.raises(SinapsiModbusError) as exc_info:
            await api._read_batch(2, 1)

        assert "ModbusLink error at address 2" in str(exc_info.value)


class TestProtocolErrorLimit:
    """Tests for protocol error limit checking."""

    def test_check_protocol_error_limit_below_threshold(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test no exception when below threshold."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        api._protocol_errors_this_cycle = MAX_PROTOCOL_ERRORS_PER_CYCLE - 1
        # Should not raise
        api._check_protocol_error_limit()

    def test_check_protocol_error_limit_at_threshold(self, mock_hass, mock_transport, mock_client):
        """Test exception raised at threshold."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        api._protocol_errors_this_cycle = MAX_PROTOCOL_ERRORS_PER_CYCLE

        with pytest.raises(SinapsiModbusError) as exc_info:
            api._check_protocol_error_limit()

        assert "Too many protocol errors" in str(exc_info.value)


class TestExtractSensorValue:
    """Tests for sensor value extraction."""

    def test_extract_sensor_value_uint16(self, mock_hass, mock_transport, mock_client):
        """Test extracting uint16 sensor value."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Create fake batch results
        batches = [[1000, 2000, 3000] + [0] * 15]  # Batch 0 has 18 registers
        batches.extend([[0] * 40 for _ in range(len(REGISTER_BATCHES) - 1)])

        # potenza_prelevata is at addr 2, batch 0, offset 0
        result = api._extract_sensor_value(batches, "potenza_prelevata")
        assert result == 1000.0

    def test_extract_sensor_value_uint32(self, mock_hass, mock_transport, mock_client):
        """Test extracting uint32 sensor value."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # energia_prelevata is at addr 5, batch 0, offset 3 (addr 5 - start 2 = 3)
        # uint32: high word at offset 3, low word at offset 4
        batches = [[0, 0, 0, 1, 0] + [0] * 13]  # High=1, Low=0 -> 65536
        batches.extend([[0] * 40 for _ in range(len(REGISTER_BATCHES) - 1)])

        result = api._extract_sensor_value(batches, "energia_prelevata")
        assert result == 65536.0

    def test_extract_sensor_value_unknown_type_raises(self, mock_hass, mock_transport, mock_client):
        """Test that unknown register type raises ValueError."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Temporarily modify SENSOR_MAP to test error path
        original_value = SENSOR_MAP.get("potenza_prelevata")
        try:
            # Inject an invalid type
            api_module.SENSOR_MAP["potenza_prelevata"] = (0, 0, "invalid_type")

            batches = [[0] * 18]
            batches.extend([[0] * 40 for _ in range(len(REGISTER_BATCHES) - 1)])

            with pytest.raises(ValueError, match="Unknown register type"):
                api._extract_sensor_value(batches, "potenza_prelevata")
        finally:
            # Restore original
            if original_value:
                api_module.SENSOR_MAP["potenza_prelevata"] = original_value


class TestProcessSensorValue:
    """Tests for sensor value processing."""

    def test_process_sensor_value_power_conversion(self, mock_hass, mock_transport, mock_client):
        """Test power values are converted from W to kW."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Find a power sensor definition
        power_sensor = next(s for s in SENSOR_ENTITIES if s["key"] == "potenza_prelevata")

        result = api._process_sensor_value(1500.0, power_sensor)
        assert result == 1.5  # 1500 W = 1.5 kW

    def test_process_sensor_value_power_preserves_watt_precision(
        self, mock_hass, mock_transport, mock_client
    ):
        """Regression: 332 W must be preserved as 0.332 kW, not truncated to 0.33 kW."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        power_sensor = next(s for s in SENSOR_ENTITIES if s["key"] == "potenza_prelevata")

        result = api._process_sensor_value(332.0, power_sensor)
        assert result == 0.332  # 332 W = 0.332 kW (1 W precision preserved)

    def test_process_sensor_value_energy_conversion(self, mock_hass, mock_transport, mock_client):
        """Test energy values are converted from Wh to kWh."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        energy_sensor = next(s for s in SENSOR_ENTITIES if s["key"] == "energia_prelevata")

        result = api._process_sensor_value(2500000.0, energy_sensor)
        assert result == 2500.0  # 2500000 Wh = 2500 kWh

    def test_process_sensor_value_energy_preserves_watthour_precision(
        self, mock_hass, mock_transport, mock_client
    ):
        """Regression: 332 Wh must be preserved as 0.332 kWh, not truncated to 0.33 kWh."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        energy_sensor = next(s for s in SENSOR_ENTITIES if s["key"] == "energia_prelevata")

        result = api._process_sensor_value(332.0, energy_sensor)
        assert result == 0.332  # 332 Wh = 0.332 kWh (1 Wh precision preserved)

    def test_process_sensor_value_non_energy_integer(self, mock_hass, mock_transport, mock_client):
        """Test non-energy values are converted to int."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # fascia_oraria_attuale has no device class for energy/power
        fascia_sensor = next(s for s in SENSOR_ENTITIES if s["key"] == "fascia_oraria_attuale")

        result = api._process_sensor_value(3.7, fascia_sensor)
        assert result == "F3"  # Converted to int (3), then F3


class TestApplySpecialValueRules:
    """Tests for special value rules."""

    def test_data_evento_max_value_returns_none(self, mock_hass, mock_transport, mock_client):
        """Test data_evento returns 'None' for MAX_EVENT_VALUE."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        result = api._apply_special_value_rules(MAX_EVENT_VALUE + 1, "data_evento")
        assert result == "None"

    def test_data_evento_valid_timestamp(self, mock_hass, mock_transport, mock_client):
        """Test data_evento converts valid timestamp."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Set tempo_residuo_distacco for calculation
        api.data["tempo_residuo_distacco"] = 0

        # Use a known timestamp
        result = api._apply_special_value_rules(
            1704067200, "data_evento"
        )  # 2024-01-01 00:00:00 UTC
        assert isinstance(result, str)
        assert "2024" in result

    def test_normal_value_passthrough(self, mock_hass, mock_transport, mock_client):
        """Test normal values pass through unchanged."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        result = api._apply_special_value_rules(12345, "some_other_key")
        assert result == 12345


class TestReadModbusAlfa:
    """Tests for read_modbus_alfa method."""

    async def test_read_modbus_alfa_success(self, mock_hass, mock_transport, mock_client):
        """Test successful modbus read."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Return enough registers for each batch
        mock_client.read_holding_registers = AsyncMock(return_value=[0] * 40)

        result = await api.read_modbus_alfa()

        assert result is True
        assert api._protocol_errors_this_cycle == 0
        # Verify derived values were calculated
        assert "potenza_consumata" in api.data
        assert "energia_consumata" in api.data

    async def test_read_modbus_alfa_batch_failure(self, mock_hass, mock_transport, mock_client):
        """Test modbus read fails when batch read fails."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        mock_client.read_holding_registers = AsyncMock(
            side_effect=ModbusConnectionError("Connection lost")
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(SinapsiModbusError) as exc_info,
        ):
            await api.read_modbus_alfa()

        assert "Failed to read modbus data" in str(exc_info.value)

    async def test_read_modbus_alfa_aborts_on_protocol_errors(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test modbus read aborts early on too many protocol errors."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Create a side effect that increments protocol_errors and raises SinapsiModbusError
        # when the threshold is reached (simulating what _read_batch does internally)
        call_count = 0

        async def mock_read_batch_with_protocol_errors(start_address, count):
            nonlocal call_count
            call_count += 1
            # Increment protocol errors each call
            api._protocol_errors_this_cycle += 1
            # After reaching threshold, _check_protocol_error_limit would be called
            if api._protocol_errors_this_cycle >= MAX_PROTOCOL_ERRORS_PER_CYCLE:
                raise SinapsiModbusError(
                    f"Too many protocol errors ({api._protocol_errors_this_cycle}), "
                    "aborting read cycle"
                )
            # Return valid data for batches that succeed
            return [0] * count

        with (
            patch.object(api, "_read_batch", side_effect=mock_read_batch_with_protocol_errors),
            pytest.raises(SinapsiModbusError) as exc_info,
        ):
            await api.read_modbus_alfa()

        assert "Too many protocol errors" in str(exc_info.value)


class TestCumulativeEnergyValidation:
    """Tests for cumulative energy value validation (protects against device reboots)."""

    def test_cumulative_energy_sensors_constant(self):
        """Test CUMULATIVE_ENERGY_SENSORS contains expected sensors."""
        assert "energia_prelevata" in CUMULATIVE_ENERGY_SENSORS
        assert "energia_immessa" in CUMULATIVE_ENERGY_SENSORS
        assert "energia_prodotta" in CUMULATIVE_ENERGY_SENSORS
        # Should not include daily or calculated sensors
        assert "energia_prelevata_giornaliera_f1" not in CUMULATIVE_ENERGY_SENSORS
        assert "energia_consumata" not in CUMULATIVE_ENERGY_SENSORS

    async def test_rejects_decreased_cumulative_energy_on_device_reboot(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test cumulative energy values preserved when device returns zeros (reboot)."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Simulate previous valid readings
        api.data["energia_prelevata"] = 7240.23
        api.data["energia_immessa"] = 500.0
        api.data["energia_prodotta"] = 300.0

        # Device reboot: all registers return 0
        mock_client.read_holding_registers = AsyncMock(return_value=[0] * 40)

        await api.read_modbus_alfa()

        # Cumulative energy values should be preserved (not overwritten with 0.0)
        assert api.data["energia_prelevata"] == 7240.23
        assert api.data["energia_immessa"] == 500.0
        assert api.data["energia_prodotta"] == 300.0

    async def test_accepts_cumulative_energy_on_first_read(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test first read from default (0.0) accepts values (no false rejection)."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Default values are 0.0 (from _initialize_data_structure)
        assert api.data["energia_prelevata"] == 0.0

        # All registers return 0 - should be accepted since previous is 0.0 (not > 0)
        mock_client.read_holding_registers = AsyncMock(return_value=[0] * 40)

        await api.read_modbus_alfa()

        # Value should be accepted (0.0 is not > 0, so validation is skipped)
        assert api.data["energia_prelevata"] == 0.0

    async def test_accepts_increased_cumulative_energy(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test increased cumulative energy values are accepted normally."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Pre-set to lower value
        api.data["energia_prelevata"] = 1000.0

        # Build batch 0 with energia_prelevata = 2000000 Wh = 2000.0 kWh
        # energia_prelevata at offset 3-4 (addr 5-6, uint32)
        # 2000000 = (30 << 16) | 33920
        batch_0 = [0] * 18
        batch_0[3] = 30  # high word
        batch_0[4] = 33920  # low word

        call_count = 0

        async def mock_read(*args, **kwargs):
            nonlocal call_count
            idx = call_count
            call_count += 1
            if idx == 0:
                return batch_0
            return [0] * 40

        mock_client.read_holding_registers = AsyncMock(side_effect=mock_read)

        await api.read_modbus_alfa()

        # energia_prelevata should be updated to the higher value
        assert api.data["energia_prelevata"] == 2000.0

    async def test_non_cumulative_sensors_not_protected(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test that non-cumulative sensors can decrease (e.g., daily midnight reset)."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Pre-set a daily sensor to a non-zero value
        api.data["energia_prelevata_giornaliera_f1"] = 100.0

        # All registers return 0 (simulating midnight reset)
        mock_client.read_holding_registers = AsyncMock(return_value=[0] * 40)

        await api.read_modbus_alfa()

        # Daily sensor SHOULD be updated to 0.0 (not protected by validation)
        assert api.data["energia_prelevata_giornaliera_f1"] == 0.0

    async def test_derived_values_use_protected_base_values(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test that derived energy values use protected (not zeroed) base values."""
        api = SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

        # Simulate previous valid readings
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0

        # Device reboot: all registers return 0
        mock_client.read_holding_registers = AsyncMock(return_value=[0] * 40)

        await api.read_modbus_alfa()

        # Derived values should use the protected base values
        # energia_auto_consumata = energia_prodotta - energia_immessa = 500 - 200 = 300
        assert api.data["energia_auto_consumata"] == 300.0
        # energia_consumata = energia_auto_consumata + energia_prelevata = 300 + 1000 = 1300
        assert api.data["energia_consumata"] == 1300.0


class TestSynchronizedEnergyCalculation:
    """Tests for synchronized derived energy calculation.

    The Alfa firmware updates energia_prodotta ~1 min before energia_immessa,
    causing our 60s polling to capture them on alternating polls. Calculating
    (prodotta - immessa) when only one has updated produces a temporary spike/dip
    that HA's TOTAL_INCREASING misinterprets as a meter reset, causing over-counting.
    The fix waits for both base sensors to update before recalculating.
    """

    def _create_api(self, mock_hass):
        """Create a test API instance."""
        return SinapsiAlfaAPI(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_TIMEOUT,
        )

    def test_first_poll_always_calculates(self, mock_hass, mock_transport, mock_client):
        """Test first poll calculates derived values (no previous tracking data)."""
        api = self._create_api(mock_hass)

        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0

        assert api._last_calc_prodotta is None

        api._calculate_derived_values()

        # Energy values should be calculated on first poll
        assert api.data["energia_auto_consumata"] == 300.0
        assert api.data["energia_consumata"] == 1300.0
        # Tracking variables should be set
        assert api._last_calc_prodotta == 500.0
        assert api._last_calc_immessa == 200.0

    def test_both_fresh_recalculates_immediately(self, mock_hass, mock_transport, mock_client):
        """Test both sensors changed since last calc → immediate recalculation."""
        api = self._create_api(mock_hass)

        # Establish baseline (first poll)
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        # Both base sensors change
        api.data["energia_prodotta"] = 510.0
        api.data["energia_immessa"] = 205.0
        api._calculate_derived_values()

        # Should recalculate with new synchronized values
        assert api.data["energia_auto_consumata"] == 305.0
        assert api.data["energia_consumata"] == 1305.0
        assert api._last_calc_prodotta == 510.0
        assert api._last_calc_immessa == 205.0

    def test_only_prodotta_fresh_skips_calculation(self, mock_hass, mock_transport, mock_client):
        """Test only prodotta changed → skip (wait for immessa to catch up)."""
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        assert api.data["energia_auto_consumata"] == 300.0

        # Only prodotta changes (immessa stale — firmware timing skew)
        api.data["energia_prodotta"] = 510.0
        api._calculate_derived_values()

        # Energy values should NOT change (skip to avoid spike)
        assert api.data["energia_auto_consumata"] == 300.0
        assert api.data["energia_consumata"] == 1300.0
        # Tracking should NOT be updated
        assert api._last_calc_prodotta == 500.0
        assert api._first_unsync_time is not None

    def test_only_immessa_fresh_skips_calculation(self, mock_hass, mock_transport, mock_client):
        """Test only immessa changed → skip (wait for prodotta)."""
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        # Only immessa changes
        api.data["energia_immessa"] = 205.0
        api._calculate_derived_values()

        # Energy values should NOT change
        assert api.data["energia_auto_consumata"] == 300.0
        assert api._first_unsync_time is not None

    def test_timeout_fallback_calculates(self, mock_hass, mock_transport, mock_client):
        """Test after SYNC_TIMEOUT_SECONDS with only one changing → calculate."""
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        # Only prodotta changes — starts timer, should wait
        api.data["energia_prodotta"] = 510.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0  # Still held
        assert api._first_unsync_time is not None

        # Simulate time passing beyond timeout
        api._first_unsync_time = time.monotonic() - SYNC_TIMEOUT_SECONDS - 1

        # Next poll hits the timeout → should calculate
        api._calculate_derived_values()

        # Now calculated with current values
        # energia_auto_consumata = 510 - 200 = 310
        assert api.data["energia_auto_consumata"] == 310.0
        assert api.data["energia_consumata"] == 1310.0
        assert api._first_unsync_time is None

    def test_neither_changed_resets_timer(self, mock_hass, mock_transport, mock_client):
        """Test neither sensor changed → timer resets, no unnecessary timeout calc."""
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        # No changes at all for many polls
        for _ in range(10):
            api._calculate_derived_values()

        # Values unchanged, timer stays None (not started)
        assert api.data["energia_auto_consumata"] == 300.0
        assert api.data["energia_consumata"] == 1300.0
        assert api._first_unsync_time is None

    def test_idle_period_does_not_poison_timer(self, mock_hass, mock_transport, mock_client):
        """Regression: idle polls must not start the unsync timer.

        Before the fix, idle polls could accumulate state that caused the
        first poll with a single-sensor update to immediately trigger
        the timeout and calculate with desynchronized values, causing oscillation.
        """
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 5000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 1000.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 800.0

        # Simulate 13 idle polls (neither sensor changes — firmware between updates)
        for _ in range(13):
            api._calculate_derived_values()

        # Timer must be None after idle polls (not started)
        assert api._first_unsync_time is None

        # Now production updates (immessa still stale) — must NOT trigger timeout
        api.data["energia_prodotta"] = 1010.0
        api._calculate_derived_values()

        # Energy value must NOT change (waiting for immessa to catch up)
        assert api.data["energia_auto_consumata"] == 800.0
        assert api._first_unsync_time is not None

        # Next poll: immessa catches up — now both fresh, calculate
        api.data["energia_immessa"] = 202.0
        api._calculate_derived_values()

        # Correct synchronized calculation: 1010 - 202 = 808
        assert api.data["energia_auto_consumata"] == 808.0
        assert api._first_unsync_time is None

    def test_oscillation_prevented_alternating_pattern(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test alternating pattern: calculation only happens when both sensors are fresh.

        Simulates the Alfa firmware behavior where prodotta updates on odd polls
        and immessa catches up on even polls. Without the fix, odd polls would
        produce artificial spikes in the calculated difference. With the fix,
        calculations only happen on even polls (both fresh), preventing oscillation.
        """
        api = self._create_api(mock_hass)

        api.data["energia_prelevata"] = 5000.0
        api.data["potenza_prelevata"] = 0.0
        api.data["potenza_immessa"] = 1.0
        api.data["potenza_prodotta"] = 2.0

        # Initial state
        api.data["energia_prodotta"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api._calculate_derived_values()

        assert api.data["energia_auto_consumata"] == 800.0

        # Simulate 5 complete alternating cycles (10 polls)
        # Each cycle: prodotta increases by 1.0, immessa by 0.2
        # → self_consumed increases by 0.8 per cycle
        alternating_data = [
            # (prodotta, immessa, should_calc)
            (1001.0, 200.0, False),  # Poll 1: prodotta up, immessa same → SKIP
            (1001.0, 200.2, True),  # Poll 2: immessa up, both fresh → CALC (800.8)
            (1002.0, 200.2, False),  # Poll 3: prodotta up → SKIP
            (1002.0, 200.4, True),  # Poll 4: immessa up → CALC (801.6)
            (1003.0, 200.4, False),  # Poll 5: prodotta up → SKIP
            (1003.0, 200.6, True),  # Poll 6: immessa up → CALC (802.4)
            (1004.0, 200.6, False),  # Poll 7: prodotta up → SKIP
            (1004.0, 200.8, True),  # Poll 8: immessa up → CALC (803.2)
            (1005.0, 200.8, False),  # Poll 9: prodotta up → SKIP
            (1005.0, 201.0, True),  # Poll 10: immessa up → CALC (804.0)
        ]

        prev_auto = 800.0
        for prodotta, immessa, should_calc in alternating_data:
            api.data["energia_prodotta"] = prodotta
            api.data["energia_immessa"] = immessa
            api._calculate_derived_values()

            curr_auto = api.data["energia_auto_consumata"]
            if not should_calc:
                # On skip polls, value must stay unchanged (no artificial spike)
                assert curr_auto == prev_auto, (
                    f"Value changed on skip poll: {prev_auto} → {curr_auto}"
                )
            else:
                # On calc polls, value should increase (both sensors fresh)
                assert curr_auto > prev_auto, (
                    f"Value did not increase on calc poll: {prev_auto} → {curr_auto}"
                )
                prev_auto = curr_auto

        # Final value should reflect the synchronized cumulative difference
        assert api.data["energia_auto_consumata"] == pytest.approx(1005.0 - 201.0)

    def test_no_export_period_timeout_allows_updates(self, mock_hass, mock_transport, mock_client):
        """Test no-export period: only prodotta changes, immessa stays constant.

        The timeout fallback allows calculation to proceed because there's
        no alternating pattern and therefore no oscillation risk.
        """
        api = self._create_api(mock_hass)

        api.data["energia_prelevata"] = 5000.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 1.0

        # Baseline: all production is self-consumed (no export)
        api.data["energia_prodotta"] = 500.0
        api.data["energia_immessa"] = 200.0  # Stays constant (no export)
        api._calculate_derived_values()

        assert api.data["energia_auto_consumata"] == 300.0

        # Only prodotta changes — starts timer, should wait
        api.data["energia_prodotta"] = 506.0
        api._calculate_derived_values()
        assert api.data["energia_auto_consumata"] == 300.0  # Held
        assert api._first_unsync_time is not None

        # Simulate time passing beyond timeout
        api._first_unsync_time = time.monotonic() - SYNC_TIMEOUT_SECONDS - 1

        # Next poll — timeout fires
        api._calculate_derived_values()

        # After timeout, value should be updated to latest
        # energia_auto_consumata = 506.0 - 200.0 = 306.0
        assert api.data["energia_auto_consumata"] == 306.0
        # energia_consumata = 306.0 + 5000.0 = 5306.0
        assert api.data["energia_consumata"] == 5306.0

    def test_power_sensors_always_calculated(self, mock_hass, mock_transport, mock_client):
        """Test power sensors (MEASUREMENT) are always calculated regardless of sync state."""
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        # Only prodotta changes (energy calc will be skipped)
        api.data["energia_prodotta"] = 510.0
        api.data["potenza_prodotta"] = 3.0
        api._calculate_derived_values()

        # Power sensors should ALWAYS update (not affected by sync logic)
        assert api.data["potenza_auto_consumata"] == 2.5  # 3.0 - 0.5
        assert api.data["potenza_consumata"] == 3.5  # 2.5 + 1.0

        # Energy sensors should NOT update (waiting for sync)
        assert api.data["energia_auto_consumata"] == 300.0

    def test_sync_timer_resets_on_both_fresh(self, mock_hass, mock_transport, mock_client):
        """Test unsync timer resets when both sensors become fresh."""
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        # One unsync poll — timer starts
        api.data["energia_prodotta"] = 510.0
        api._calculate_derived_values()
        assert api._first_unsync_time is not None

        # Now immessa also changes → both fresh → timer resets
        api.data["energia_immessa"] = 205.0
        api._calculate_derived_values()
        assert api._first_unsync_time is None
        assert api.data["energia_auto_consumata"] == 305.0

    def test_consumata_updates_when_only_prelevata_changes(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test energia_consumata updates when only prelevata changes.

        This is the critical test for the beta.3 fix: when production stops,
        prodotta/immessa stop changing so should_calculate stays False.
        But prelevata (import) keeps growing and energia_consumata must reflect that.
        """
        api = self._create_api(mock_hass)

        # Establish baseline (first poll)
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        assert api.data["energia_auto_consumata"] == 300.0  # 500 - 200
        assert api.data["energia_consumata"] == 1300.0  # 300 + 1000

        # Only prelevata changes — prodotta and immessa unchanged
        api.data["energia_prelevata"] = 1001.0
        api._calculate_derived_values()

        # auto_consumata must stay frozen (sync guard holds — neither is fresh)
        assert api.data["energia_auto_consumata"] == 300.0
        # consumata must update to reflect new prelevata
        assert api.data["energia_consumata"] == 1301.0  # 300 + 1001

    def test_night_scenario_full_cycle(self, mock_hass, mock_transport, mock_client):
        """Test nighttime scenario: only prelevata changes for many polls.

        Simulates evening/night when PV production stops. energia_prodotta and
        energia_immessa stop changing, but energia_prelevata (import from grid)
        keeps growing. energia_consumata must track that growth.
        """
        api = self._create_api(mock_hass)

        # Daytime baseline
        api.data["energia_prelevata"] = 5000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 1000.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.0
        api.data["potenza_prodotta"] = 0.0
        api._calculate_derived_values()

        baseline_auto = api.data["energia_auto_consumata"]
        assert baseline_auto == 800.0  # 1000 - 200

        # 10 nighttime polls: only prelevata increases (1.0 per poll)
        for i in range(1, 11):
            api.data["energia_prelevata"] = 5000.0 + i
            api._calculate_derived_values()

            # auto_consumata must stay frozen (no production changes)
            assert api.data["energia_auto_consumata"] == baseline_auto
            # consumata must increase with prelevata
            expected_consumata = baseline_auto + 5000.0 + i
            assert api.data["energia_consumata"] == expected_consumata

    def test_day_to_night_transition(self, mock_hass, mock_transport, mock_client):
        """Test full lifecycle: daytime → transition → nighttime.

        Verifies energia_consumata tracks correctly through all phases:
        1. Daytime: both sensors fresh, full recalculation
        2. Transition: last firmware update (one fresh → timeout → calc)
        3. Nighttime: only prelevata changes, consumata keeps updating
        """
        api = self._create_api(mock_hass)

        # Phase 1: Daytime — both sensors fresh
        api.data["energia_prelevata"] = 5000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 1000.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        assert api.data["energia_auto_consumata"] == 800.0
        assert api.data["energia_consumata"] == 5800.0  # 800 + 5000

        # Both sensors update together
        api.data["energia_prodotta"] = 1010.0
        api.data["energia_immessa"] = 202.0
        api.data["energia_prelevata"] = 5001.0
        api._calculate_derived_values()

        assert api.data["energia_auto_consumata"] == 808.0  # 1010 - 202
        assert api.data["energia_consumata"] == 5809.0  # 808 + 5001

        # Phase 2: Transition — last firmware update, prodotta changes alone
        api.data["energia_prodotta"] = 1011.0
        api.data["energia_prelevata"] = 5002.0
        api._calculate_derived_values()

        # auto_consumata frozen (waiting for immessa), consumata updates with prelevata
        assert api.data["energia_auto_consumata"] == 808.0
        assert api.data["energia_consumata"] == 5810.0  # 808 + 5002

        # Simulate time passing beyond timeout
        api._first_unsync_time = time.monotonic() - SYNC_TIMEOUT_SECONDS - 1

        # Prelevata keeps growing during wait
        api.data["energia_prelevata"] = 5004.0
        api._calculate_derived_values()

        # After timeout: auto_consumata recalculated, consumata uses latest prelevata
        assert api.data["energia_auto_consumata"] == 809.0  # 1011 - 202
        assert api.data["energia_consumata"] == 5813.0  # 809 + 5004

        # Phase 3: Nighttime — no more production changes, only prelevata
        frozen_auto = api.data["energia_auto_consumata"]
        latest_prelevata = api.data["energia_prelevata"]
        for i in range(5):
            api.data["energia_prelevata"] = latest_prelevata + i + 1
            api._calculate_derived_values()

            assert api.data["energia_auto_consumata"] == frozen_auto
            assert api.data["energia_consumata"] == frozen_auto + latest_prelevata + i + 1

    def test_consumata_uses_latest_prelevata_after_sync_calc(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test consumata uses latest prelevata even when should_calculate is True.

        When both prodotta and immessa are fresh, auto_consumata is recalculated.
        energia_consumata must use the latest prelevata value (which may have also
        changed), not a stale one.
        """
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        assert api.data["energia_consumata"] == 1300.0  # 300 + 1000

        # All three change simultaneously
        api.data["energia_prodotta"] = 510.0
        api.data["energia_immessa"] = 205.0
        api.data["energia_prelevata"] = 1005.0
        api._calculate_derived_values()

        # auto_consumata = 510 - 205 = 305
        assert api.data["energia_auto_consumata"] == 305.0
        # consumata must use latest prelevata, not stale 1000
        assert api.data["energia_consumata"] == 1310.0  # 305 + 1005

    def test_debug_log_only_when_waiting(self, mock_hass, mock_transport, mock_client):
        """Test debug log fires only when one sensor is fresh (actual waiting state).

        The log should NOT fire when neither sensor is fresh (idle polls),
        as that would create misleading log spam during nighttime hours.
        """
        api = self._create_api(mock_hass)

        # Establish baseline
        api.data["energia_prelevata"] = 1000.0
        api.data["energia_immessa"] = 200.0
        api.data["energia_prodotta"] = 500.0
        api.data["potenza_prelevata"] = 1.0
        api.data["potenza_immessa"] = 0.5
        api.data["potenza_prodotta"] = 2.0
        api._calculate_derived_values()

        with patch.object(api_module, "log_debug") as mock_log:
            # Scenario 1: Neither sensor changed (idle poll) — NO log
            api._calculate_derived_values()
            mock_log.assert_not_called()

            # Scenario 2: Only prodotta changes (waiting for immessa) — YES log
            api.data["energia_prodotta"] = 510.0
            api._calculate_derived_values()
            assert mock_log.call_count == 1

            mock_log.reset_mock()

            # Scenario 3: Both change (sync calc succeeds) — NO log
            api.data["energia_immessa"] = 205.0
            api._calculate_derived_values()
            mock_log.assert_not_called()

            # Scenario 4: Neither changed after sync (idle) — NO log
            api._calculate_derived_values()
            mock_log.assert_not_called()
