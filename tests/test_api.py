"""Tests for Sinapsi Alfa API."""

from unittest.mock import AsyncMock, MagicMock, patch

from modbuslink import (
    ConnectionError as ModbusConnectionError,
    CRCError,
    InvalidResponseError,
    ModbusException,
    ModbusLinkError,
    TimeoutError as ModbusTimeoutError,
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
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    MANUFACTURER,
    MAX_EVENT_VALUE,
    MODEL,
    REGISTER_BATCHES,
    SENSOR_ENTITIES,
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
        with pytest.raises(ValueError, match="Port .* is out of valid range"):
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
        """Test batch read retries on timeout error."""
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

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await api._read_batch(2, 2)

        assert result == expected_data

    async def test_read_batch_invalid_response_resets_connection(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read resets connection on InvalidResponseError."""
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
                InvalidResponseError("Transaction ID mismatch"),
                expected_data,
            ]
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch.object(api, "_reset_connection", new_callable=AsyncMock) as mock_reset,
        ):
            result = await api._read_batch(2, 1)

        assert result == expected_data
        mock_reset.assert_called_once()
        assert api._protocol_errors_this_cycle == 1

    async def test_read_batch_crc_error_resets_connection(
        self, mock_hass, mock_transport, mock_client
    ):
        """Test batch read resets connection on CRCError."""
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
                CRCError("CRC mismatch"),
                expected_data,
            ]
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch.object(api, "_reset_connection", new_callable=AsyncMock) as mock_reset,
        ):
            result = await api._read_batch(2, 1)

        assert result == expected_data
        mock_reset.assert_called_once()

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
