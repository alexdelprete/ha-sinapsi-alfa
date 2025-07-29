"""API Platform for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import asyncio
import logging
from typing import Any

from getmac import getmac
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ConnectionException, ModbusException

from .const import (
    DEFAULT_SLAVE_ID,
    DEFAULT_SENSOR_VALUE,
    INVALID_DISTACCO_VALUE,
    MANUFACTURER,
    MAX_EVENT_VALUE,
    MAX_RETRY_ATTEMPTS,
    MIN_SCAN_INTERVAL,
    MODEL,
    SENSOR_ENTITIES,
    SOCKET_TIMEOUT,
)
from .helpers import unix_timestamp_to_iso8601_local_tz

# from pymodbus.payload import BinaryPayloadDecoder
from .modbuspayload import BinaryPayloadDecoder

_LOGGER = logging.getLogger(__name__)


class SinapsiConnectionError(Exception):
    """Sinapsi-specific connection error."""

    def __init__(self, message: str, host: str | None = None, port: int | None = None):
        """Initialize the connection error.

        Args:
            message: Error message
            host: Host that failed to connect (optional)
            port: Port that failed to connect (optional)

        """

        self.host = host
        self.port = port
        super().__init__(message)


class SinapsiModbusError(Exception):
    """Sinapsi-specific Modbus error."""

    def __init__(
        self, message: str, address: int | None = None, operation: str | None = None
    ):
        """Initialize the Modbus error.

        Args:
            message: Error message
            address: Modbus register address that failed (optional)
            operation: Modbus operation that failed (optional)

        """
        self.address = address
        self.operation = operation
        super().__init__(message)


class SinapsiAlfaAPI:
    """Thread safe wrapper class for pymodbus."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        host: str,
        port: int,
        scan_interval: int,
    ):
        """Initialize the Modbus API Client.

        Args:
            hass: HomeAssistant instance
            name: Device name
            host: Device IP address
            port: Modbus TCP port
            scan_interval: Update interval in seconds

        Raises:
            ValueError: If any parameter is invalid

        """
        # Input validation
        if not host or not isinstance(host, str):
            raise ValueError("Host must be a non-empty string")
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError("Port must be an integer between 1 and 65535")
        if not isinstance(scan_interval, int):
            raise ValueError("Scan interval must be an integer")
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")

        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._slave_id = DEFAULT_SLAVE_ID
        self._update_interval = scan_interval
        # Ensure ModBus Timeout is 1s less than scan_interval
        # https://github.com/binsentsu/home-assistant-solaredge-modbus/pull/183
        self._timeout = self._update_interval - 1
        self._client = AsyncModbusTcpClient(
            host=self._host, port=self._port, timeout=self._timeout
        )
        self._lock = asyncio.Lock()
        self._uid = ""  # Initialize empty, will be set during first data fetch
        self._sensors = []
        self.data = {}
        # Initialize ModBus data structure before first read
        self._initialize_data_structure()

    def _initialize_data_structure(self) -> None:
        """Initialize the data structure with default values."""
        # Get sensor keys from SENSOR_ENTITIES, excluding calculated ones
        sensor_keys = [
            sensor["key"]
            for sensor in SENSOR_ENTITIES
            if sensor["modbus_type"] != "calcolato"
        ]

        # Initialize sensor data with default values
        for key in sensor_keys:
            self.data[key] = DEFAULT_SENSOR_VALUE

        # Initialize metadata
        self.data.update(
            {
                "manufact": MANUFACTURER,
                "model": MODEL,
                "sn": "",  # Will be set when MAC address is retrieved
            }
        )

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._name

    @property
    def host(self) -> str:
        """Return the hostname."""
        return self._host

    @property
    def uid(self) -> str:
        """Return the unique id."""
        return self._uid

    async def get_mac_address(self) -> str:
        """Get mac address from ip/hostname with improved retry logic."""
        import random  # Import here to avoid top-level import

        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # Only check port on first attempt or periodically
                if attempt == 0 or attempt % 3 == 0:
                    port_available = await self.check_port()
                    _LOGGER.debug(
                        f"Port check attempt {attempt + 1}: {'SUCCESS' if port_available else 'FAILED'}"
                    )

                mac_address = getmac.get_mac_address(
                    hostname=self._host, network_request=False
                )

                if mac_address:
                    mac_address = mac_address.replace(":", "").upper()
                    _LOGGER.debug(
                        f"MAC address found on attempt {attempt + 1}: {mac_address}"
                    )
                    return mac_address

                # Exponential backoff with jitter for remaining attempts
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    delay = min(2**attempt + random.uniform(0, 1), 10)
                    _LOGGER.debug(
                        f"MAC retrieval attempt {attempt + 1} failed, retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)

            except Exception as e:
                _LOGGER.debug(f"MAC retrieval attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    delay = min(2**attempt + random.uniform(0, 1), 10)
                    await asyncio.sleep(delay)

        _LOGGER.debug("MAC address not found after all attempts")
        return ""

    async def check_port(self) -> bool:
        """Check if port is available."""
        async with self._lock:
            sock_timeout = SOCKET_TIMEOUT
            _LOGGER.debug(
                f"Check_Port: opening socket on {self._host}:{self._port} with a {sock_timeout}s timeout."
            )

            # Use asyncio for non-blocking socket operations
            try:
                # Create connection with timeout
                future = asyncio.open_connection(self._host, self._port)
                reader, writer = await asyncio.wait_for(future, timeout=sock_timeout)

                _LOGGER.debug(
                    f"Check_Port (SUCCESS): port open on {self._host}:{self._port}"
                )

                # Clean up the connection
                writer.close()
                await writer.wait_closed()
                return True

            except (TimeoutError, ConnectionRefusedError, OSError) as e:
                _LOGGER.debug(
                    f"Check_Port (ERROR): port not available on {self._host}:{self._port} - error: {e}"
                )
                return False

    async def close(self):
        """Disconnect client."""
        try:
            if self._client.connected:
                _LOGGER.debug("Closing Modbus TCP connection")
                async with self._lock:
                    self._client.close()
                    return True
            else:
                _LOGGER.debug("Modbus TCP connection already closed")
        except ConnectionException as connect_error:
            _LOGGER.debug(f"Close Connection connect_error: {connect_error}")
            raise SinapsiConnectionError(
                f"Connection failed: {connect_error}", self._host, self._port
            ) from connect_error

    async def connect(self):
        """Connect client."""
        _LOGGER.debug(
            f"API Client connect to IP: {self._host} port: {self._port} timeout: {self._timeout}"
        )
        if await self.check_port():
            _LOGGER.debug("Inverter ready for Modbus TCP connection")
            try:
                async with self._lock:
                    await self._client.connect()
                if not self._client.connected:
                    raise SinapsiConnectionError(
                        f"Failed to connect to {self._host}:{self._port} timeout: {self._timeout}",
                        self._host,
                        self._port,
                    )
                else:
                    _LOGGER.debug("Modbus TCP Client connected")
                    return True
            except ModbusException:
                raise SinapsiConnectionError(
                    f"Failed to connect to {self._host}:{self._port} timeout: {self._timeout}",
                    self._host,
                    self._port,
                )
        else:
            _LOGGER.debug("Inverter not ready for Modbus TCP connection")
            raise SinapsiConnectionError(
                f"Inverter not active on {self._host}:{self._port}",
                self._host,
                self._port,
            )

    async def read_holding_registers(self, address: int, count: int) -> Any | None:
        """Read holding registers."""

        try:
            async with self._lock:
                return await self._client.read_holding_registers(
                    address=address, count=count, slave=self._slave_id
                )  # type: ignore
        except ConnectionException as connect_error:
            _LOGGER.debug(f"Read Holding Registers connect_error: {connect_error}")
            raise SinapsiConnectionError(
                f"Connection failed: {connect_error}", self._host, self._port
            ) from connect_error
        except ModbusException as modbus_error:
            _LOGGER.debug(f"Read Holding Registers modbus_error: {modbus_error}")
            raise SinapsiModbusError(
                f"Modbus operation failed: {modbus_error}"
            ) from modbus_error

    def _decode_register_value(self, read_data, reg_type: str) -> float:
        """Decode register value based on type."""
        decoder = BinaryPayloadDecoder.fromRegisters(
            read_data.registers, byteorder=Endian.BIG
        )

        if reg_type == "uint16":
            return round(float(decoder.decode_16bit_uint()), 2)
        elif reg_type == "uint32":
            return round(float(decoder.decode_32bit_uint()), 2)
        else:
            raise ValueError(f"Unsupported register type: {reg_type}")

    def _process_sensor_value(self, value: float, sensor: dict[str, Any]) -> Any:
        """Process sensor value with unit conversion and special handling."""
        reg_key = sensor["key"]
        reg_dev_class = sensor["device_class"]

        # Unit conversion for power/energy
        if reg_dev_class in [SensorDeviceClass.ENERGY, SensorDeviceClass.POWER]:
            value = round(value / 1000, 2)  # W/Wh to kW/kWh
        else:
            value = int(value)

        # Special value handling
        return self._apply_special_value_rules(value, reg_key)

    def _apply_special_value_rules(self, value: Any, reg_key: str) -> Any:
        """Apply special rules for specific sensor values."""
        if reg_key == "tempo_residuo_distacco" and value == INVALID_DISTACCO_VALUE:
            return 0

        if reg_key == "data_evento":
            if value > MAX_EVENT_VALUE:
                return "None"
            else:
                return unix_timestamp_to_iso8601_local_tz(
                    value + self.data["tempo_residuo_distacco"]
                )

        if reg_key == "fascia_oraria_attuale":
            return f"F{value}"

        return value

    def _calculate_derived_values(self) -> None:
        """Calculate derived values from base measurements."""
        self.data["potenza_auto_consumata"] = (
            self.data["potenza_prodotta"] - self.data["potenza_immessa"]
        )
        self.data["potenza_consumata"] = (
            self.data["potenza_auto_consumata"] + self.data["potenza_prelevata"]
        )
        self.data["energia_auto_consumata"] = (
            self.data["energia_prodotta"] - self.data["energia_immessa"]
        )
        self.data["energia_consumata"] = (
            self.data["energia_auto_consumata"] + self.data["energia_prelevata"]
        )

    async def _read_and_process_sensor(self, sensor: dict[str, Any]) -> None:
        """Read and process a single sensor."""
        reg_key = sensor["key"]
        reg_addr = sensor["modbus_addr"]
        reg_type = sensor["modbus_type"]
        reg_count = 1 if reg_type == "uint16" else 2

        _LOGGER.debug(f"Reading {reg_key} at address {reg_addr}")

        read_data = await self.read_holding_registers(reg_addr, reg_count)
        raw_value = self._decode_register_value(read_data, reg_type)
        processed_value = self._process_sensor_value(raw_value, sensor)

        self.data[reg_key] = processed_value
        _LOGGER.debug(f"Processed {reg_key}: {processed_value}")

    async def async_get_data(self) -> bool:
        """Read Data Function."""

        try:
            if await self.connect():
                # Set MAC address if not already set
                if not self._uid:
                    self._uid = await self.get_mac_address()
                    self.data["sn"] = self._uid

                _LOGGER.debug(
                    f"Start Get data (Host: {self._host} - Port: {self._port})",
                )
                # Now we can call the async method directly
                result = await self.read_modbus_alfa()
                await self.close()
                _LOGGER.debug("End Get data")
                if result:
                    _LOGGER.debug("Get Data Result: valid")
                    return True
                else:
                    _LOGGER.debug("Get Data Result: invalid")
                    return False
            else:
                _LOGGER.debug("Get Data failed: client not connected")
                return False
        except ConnectionException as connect_error:
            _LOGGER.debug(f"Async Get Data connect_error: {connect_error}")
            raise SinapsiConnectionError(
                f"Connection failed: {connect_error}", self._host, self._port
            ) from connect_error
        except ModbusException as modbus_error:
            _LOGGER.debug(f"Async Get Data modbus_error: {modbus_error}")
            raise SinapsiModbusError(
                f"Modbus operation failed: {modbus_error}"
            ) from modbus_error

    async def read_modbus_alfa(self) -> bool:
        """Read Alfa modbus registers."""
        try:
            for sensor in SENSOR_ENTITIES:
                if sensor["modbus_type"] == "calcolato":
                    self._calculate_derived_values()
                else:
                    await self._read_and_process_sensor(sensor)
            return True
        except Exception as error:
            _LOGGER.debug(f"read_modbus_alfa failed: {error}")
            raise SinapsiModbusError(f"Failed to read modbus data: {error}") from error
