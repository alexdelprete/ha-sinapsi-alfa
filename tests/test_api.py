"""Tests for Sinapsi Alfa API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sinapsi_alfa.api import (
    SinapsiAlfaAPI,
    SinapsiConnectionError,
    SinapsiModbusError,
)
from custom_components.sinapsi_alfa.const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    MANUFACTURER,
    MODEL,
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
        mock_client.read_holding_registers = AsyncMock(
            return_value=[0] * 40
        )
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
        error = SinapsiConnectionError(
            "Connection timeout", host=TEST_HOST, port=TEST_PORT
        )

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
        error = SinapsiModbusError(
            "Register read failed", address=100, operation="read_holding"
        )

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

    async def test_async_get_data_port_not_available(
        self, mock_hass, mock_transport, mock_client
    ):
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

    async def test_async_get_data_skip_mac_detection(
        self, mock_hass, mock_transport, mock_client
    ):
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
