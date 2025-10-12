"""API Platform for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import asyncio
import logging
import time
from typing import Any

from getmac import getmac
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException

from .const import (
    DEFAULT_DEVICE_ID,
    DEFAULT_SENSOR_VALUE,
    INVALID_DISTACCO_VALUE,
    MANUFACTURER,
    MAX_EVENT_VALUE,
    MAX_PORT,
    MAX_RETRY_ATTEMPTS,
    MIN_PORT,
    MODEL,
    SENSOR_ENTITIES,
    SOCKET_TIMEOUT,
)
from .helpers import log_debug, log_error, unix_timestamp_to_iso8601_local_tz
from .pymodbus_constants import Endian
from .pymodbus_payload import BinaryPayloadDecoder

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

        """

        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._device_id = DEFAULT_DEVICE_ID
        self._update_interval = scan_interval
        # Use a reasonable fixed timeout for Modbus operations
        # The previous logic (scan_interval - 1) caused excessively long timeouts
        # that interfered with pymodbus retry mechanism
        self._timeout = min(5.0, self._update_interval / 2)
        self._client = AsyncModbusTcpClient(
            host=self._host, port=self._port, timeout=self._timeout
        )
        self._lock = asyncio.Lock()
        self._uid = ""  # Initialize empty, will be set during first data fetch
        self._sensors = []
        self.data = {}
        # Connection health tracking
        self._connection_healthy = False
        self._last_successful_read = None
        # Initialize ModBus data structure before first read
        self._initialize_data_structure()

        # Validate configuration parameters
        self._validate_port(self._port)

    def _validate_port(self, port: int) -> None:
        """Validate port number is within valid range.

        Args:
            port: Port number to validate

        Raises:
            ValueError: If port is out of range

        """
        if not MIN_PORT <= port <= MAX_PORT:
            raise ValueError(
                f"Port {port} is out of valid range ({MIN_PORT}-{MAX_PORT})"
            )

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
                    log_debug(
                        _LOGGER,
                        "get_mac_address",
                        f"Port check attempt {attempt + 1}",
                        result="SUCCESS" if port_available else "FAILED",
                    )

                mac_address = getmac.get_mac_address(
                    hostname=self._host, network_request=True
                )

                if mac_address:
                    mac_address = mac_address.replace(":", "").upper()
                    log_debug(
                        _LOGGER,
                        "get_mac_address",
                        f"MAC address found on attempt {attempt + 1}",
                        mac=mac_address,
                    )
                    return mac_address

                # Exponential backoff with jitter for remaining attempts
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    delay = min(2**attempt + random.uniform(0, 1), 10)
                    log_debug(
                        _LOGGER,
                        "get_mac_address",
                        f"MAC retrieval attempt {attempt + 1} failed, retrying",
                        delay_s=f"{delay:.1f}",
                    )
                    await asyncio.sleep(delay)

            except Exception as e:
                log_debug(
                    _LOGGER,
                    "get_mac_address",
                    f"MAC retrieval attempt {attempt + 1} failed",
                    error=e,
                )
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    delay = min(2**attempt + random.uniform(0, 1), 10)
                    await asyncio.sleep(delay)

        log_debug(
            _LOGGER, "get_mac_address", "MAC address not found after all attempts"
        )
        # Return a fallback unique identifier based on host:port
        fallback_id = f"{self._host.replace('.', '')}_{self._port}"
        log_debug(
            _LOGGER, "get_mac_address", "Using fallback ID", fallback_id=fallback_id
        )
        return fallback_id

    async def check_port(self) -> bool:
        """Check if port is available."""
        async with self._lock:
            sock_timeout = SOCKET_TIMEOUT
            log_debug(
                _LOGGER,
                "check_port",
                "Opening socket",
                host=self._host,
                port=self._port,
                timeout=f"{sock_timeout}s",
            )

            # Use asyncio for non-blocking socket operations
            try:
                # Create connection with timeout
                future = asyncio.open_connection(self._host, self._port)
                reader, writer = await asyncio.wait_for(future, timeout=sock_timeout)

                log_debug(
                    _LOGGER,
                    "check_port",
                    "Port available",
                    host=self._host,
                    port=self._port,
                )

                # Clean up the connection
                writer.close()
                await writer.wait_closed()
                return True

            except (TimeoutError, ConnectionRefusedError, OSError) as e:
                log_debug(
                    _LOGGER,
                    "check_port",
                    "Port not available",
                    host=self._host,
                    port=self._port,
                    error=e,
                )
                return False

    async def close(self):
        """Disconnect client."""
        try:
            if self._client.connected:
                log_debug(_LOGGER, "close", "Closing Modbus TCP connection")
                async with self._lock:
                    self._client.close()
                    self._connection_healthy = False
                    return True
            else:
                log_debug(_LOGGER, "close", "Modbus TCP connection already closed")
        except ConnectionException as connect_error:
            log_error(
                _LOGGER,
                "close",
                "Close connection error",
                error=connect_error,
            )
            raise SinapsiConnectionError(
                f"Connection failed: {connect_error}", self._host, self._port
            ) from connect_error

    async def connect(self):
        """Connect client."""
        log_debug(
            _LOGGER,
            "connect",
            "Connecting to device",
            host=self._host,
            port=self._port,
            timeout=self._timeout,
        )
        if await self.check_port():
            log_debug(_LOGGER, "connect", "Device ready for Modbus TCP connection")
            start_time = time.time()
            try:
                async with self._lock:
                    await self._client.connect()
                connect_duration = time.time() - start_time
                log_debug(
                    _LOGGER,
                    "connect",
                    "Connection attempt completed",
                    duration_s=f"{connect_duration:.3f}",
                )
                if not self._client.connected:
                    self._connection_healthy = False
                    raise SinapsiConnectionError(
                        f"Failed to connect to {self._host}:{self._port} timeout: {self._timeout}",
                        self._host,
                        self._port,
                    )
                else:
                    log_debug(_LOGGER, "connect", "Modbus TCP Client connected")
                    self._connection_healthy = True
                    return True
            except Exception as e:
                self._connection_healthy = False
                log_error(
                    _LOGGER,
                    "connect",
                    "Connection failed",
                    error_type=type(e).__name__,
                    error=e,
                )
                raise SinapsiConnectionError(
                    f"Failed to connect to {self._host}:{self._port} timeout: {self._timeout} - {type(e).__name__}: {e}",
                    self._host,
                    self._port,
                ) from e
        else:
            log_debug(_LOGGER, "connect", "Device not ready for Modbus TCP connection")
            self._connection_healthy = False
            raise SinapsiConnectionError(
                f"Device not active on {self._host}:{self._port}",
                self._host,
                self._port,
            )

    async def read_holding_registers(self, address: int, count: int) -> Any | None:
        """Read holding registers."""

        try:
            async with self._lock:
                result = await self._client.read_holding_registers(
                    address=address, count=count, device_id=self._device_id
                )  # type: ignore
            if result.isError():
                log_debug(
                    _LOGGER,
                    "read_holding_registers",
                    "Modbus error response",
                    address=address,
                    count=count,
                    result=result,
                )
                raise SinapsiModbusError(
                    f"Device reported error: {result}",
                    address=address,
                    operation="read_holding_registers",
                )
            return result
        except ConnectionException as connect_error:
            log_error(
                _LOGGER,
                "read_holding_registers",
                "Connection error",
                address=address,
                error=connect_error,
            )
            self._connection_healthy = False
            raise SinapsiConnectionError(
                f"Connection failed: {connect_error}", self._host, self._port
            ) from connect_error
        except ModbusException as modbus_error:
            log_error(
                _LOGGER,
                "read_holding_registers",
                "Modbus error",
                address=address,
                error=modbus_error,
            )
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

        log_debug(
            _LOGGER, "_read_and_process_sensor", f"Reading {reg_key}", address=reg_addr
        )

        read_data = await self.read_holding_registers(reg_addr, reg_count)
        raw_value = self._decode_register_value(read_data, reg_type)
        processed_value = self._process_sensor_value(raw_value, sensor)

        self.data[reg_key] = processed_value
        log_debug(
            _LOGGER,
            "_read_and_process_sensor",
            f"Processed {reg_key}",
            value=processed_value,
        )

    async def async_get_data(self) -> bool:
        """Read Data Function."""

        try:
            if await self.connect():
                # Set MAC address if not already set
                if not self._uid:
                    self._uid = await self.get_mac_address()
                    self.data["sn"] = self._uid

                log_debug(
                    _LOGGER,
                    "async_get_data",
                    "Start data collection",
                    host=self._host,
                    port=self._port,
                )
                # Now we can call the async method directly
                result = await self.read_modbus_alfa()
                await self.close()
                log_debug(_LOGGER, "async_get_data", "Data collection completed")
                if result:
                    log_debug(_LOGGER, "async_get_data", "Data validation: valid")
                    self._connection_healthy = True
                    self._last_successful_read = time.time()
                    return True
                else:
                    log_debug(_LOGGER, "async_get_data", "Data validation: invalid")
                    return False
            else:
                log_debug(
                    _LOGGER,
                    "async_get_data",
                    "Data collection failed: client not connected",
                )
                self._connection_healthy = False
                return False
        except ConnectionException as connect_error:
            log_error(
                _LOGGER,
                "async_get_data",
                "Connection error during data collection",
                error=connect_error,
            )
            self._connection_healthy = False
            raise SinapsiConnectionError(
                f"Connection failed: {connect_error}", self._host, self._port
            ) from connect_error
        except ModbusException as modbus_error:
            log_error(
                _LOGGER,
                "async_get_data",
                "Modbus error during data collection",
                error=modbus_error,
            )
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
            log_error(
                _LOGGER, "read_modbus_alfa", "Failed to read modbus data", error=error
            )
            raise SinapsiModbusError(f"Failed to read modbus data: {error}") from error
