"""API Platform for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import asyncio
import contextlib
import logging
import random
import socket
import time
from typing import Any, cast

from getmac import getmac  # type: ignore[import-untyped]
from modbuslink import (
    AsyncModbusClient,
    AsyncTcpTransport,
    ConnectError as ModbusConnectionError,
    CrcError,
    InvalidReplyError,
    Language,
    ModbusException,
    ModbusLinkError,
    TimeOutError as ModbusTimeoutError,
    set_language,
)

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_DEVICE_ID,
    DEFAULT_SENSOR_VALUE,
    DEFAULT_TIMEOUT,
    INVALID_DISTACCO_VALUE,
    MANUFACTURER,
    MAX_EVENT_VALUE,
    MAX_PORT,
    MAX_RETRY_ATTEMPTS,
    MIN_PORT,
    MODEL,
    REGISTER_BATCHES,
    SENSOR_ENTITIES,
)
from .helpers import log_debug, log_error, log_warning, unix_timestamp_to_iso8601_local_tz

# Configure ModbusLink to use English for logs AND errors
set_language(Language.EN)

_LOGGER = logging.getLogger(__name__)

# Batch read constants
BATCH_MAX_RETRIES = 3
BATCH_RETRY_DELAY_CONNECTION = 1.0  # seconds
BATCH_RETRY_DELAY_TIMEOUT = 2.0  # seconds
BATCH_RETRY_DELAY_PROTOCOL = 3.0  # seconds - longer delay for protocol errors
MAX_PROTOCOL_ERRORS_PER_CYCLE = 3  # Abort cycle early if too many protocol errors


def _build_sensor_map() -> dict[str, tuple[int, int, str]]:
    """Build sensor-to-batch mapping from SENSOR_ENTITIES and REGISTER_BATCHES.

    Returns dict: sensor_key -> (batch_index, offset, modbus_type)
    Offset is calculated as: modbus_addr - batch_start_address
    """
    sensor_map: dict[str, tuple[int, int, str]] = {}

    for sensor in SENSOR_ENTITIES:
        sensor_def = cast(dict[str, Any], sensor)
        if sensor_def["modbus_type"] == "calcolato":
            continue  # Skip calculated sensors

        addr = sensor_def["modbus_addr"]
        # Skip sensors without a modbus address (shouldn't happen after calcolato check)
        if addr is None or not isinstance(addr, int):
            continue

        key = str(sensor_def["key"])
        modbus_type = str(sensor_def["modbus_type"])

        # Find which batch contains this address
        for batch_id, (start, count) in enumerate(REGISTER_BATCHES):
            if start <= addr < start + count:
                offset = addr - start
                sensor_map[key] = (batch_id, offset, modbus_type)
                break

    return sensor_map


# Build mapping at module load time (once)
SENSOR_MAP = _build_sensor_map()


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

    def __init__(self, message: str, address: int | None = None, operation: str | None = None):
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
    """Thread safe wrapper class for ModbusLink."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        host: str,
        port: int,
        scan_interval: int,
        timeout: int = DEFAULT_TIMEOUT,
        skip_mac_detection: bool = False,
    ):
        """Initialize the Modbus API Client.

        Args:
            hass: HomeAssistant instance
            name: Device name
            host: Device IP address
            port: Modbus TCP port
            scan_interval: Update interval in seconds
            timeout: Connection timeout in seconds (default: 10)
            skip_mac_detection: Skip MAC detection for VPN connections (default: False)

        """

        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._device_id = DEFAULT_DEVICE_ID
        self._update_interval = scan_interval
        # User-configurable timeout for Modbus operations
        self._timeout = float(timeout)
        # Skip MAC detection for VPN connections
        self._skip_mac_detection = skip_mac_detection
        # ModbusLink uses separate transport and client objects
        self._transport = AsyncTcpTransport(
            host=self._host,
            port=self._port,
            timeout=self._timeout,
        )
        self._client = AsyncModbusClient(self._transport)
        self._uid = ""  # Initialize empty, will be set during first data fetch
        self._sensors: list[dict[str, Any]] = []
        self.data: dict[str, Any] = {}
        # Connection health tracking
        self._connection_healthy = False
        self._last_successful_read: float | None = None
        # Protocol error tracking for early abort
        self._protocol_errors_this_cycle = 0
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
            raise ValueError(f"Port {port} is out of valid range ({MIN_PORT}-{MAX_PORT})")

    def _initialize_data_structure(self) -> None:
        """Initialize the data structure with default values."""
        # Get sensor keys from SENSOR_ENTITIES, excluding calculated ones
        sensor_keys: list[str] = [
            str(sensor["key"]) for sensor in SENSOR_ENTITIES if sensor["modbus_type"] != "calcolato"
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

    async def close(self) -> None:
        """Close the Modbus connection and clean up resources.

        Note: When using context manager pattern (async with self._client),
        the connection is already closed after each poll cycle. This method
        ensures clean shutdown during integration unload.
        """
        log_debug(_LOGGER, "close", "Closing API connection")
        with contextlib.suppress(OSError):
            await self._transport.close()
        self._connection_healthy = False
        log_debug(_LOGGER, "close", "API connection closed")

    async def _flush_buffer(self) -> int:
        """Flush the receive buffer to clear stale responses.

        Uses ModbusLink 1.4.2+ flush() method to discard any pending data
        without closing the connection. This is the recommended first-line
        recovery for timeout and protocol errors.

        Returns:
            Number of bytes discarded from the buffer

        """
        try:
            discarded = await self._transport.flush()
        except OSError as e:
            log_warning(_LOGGER, "_flush_buffer", "Flush failed", error=e)
            return 0
        else:
            if discarded > 0:
                log_debug(
                    _LOGGER,
                    "_flush_buffer",
                    "Flushed stale data from buffer",
                    bytes_discarded=discarded,
                )
            return discarded

    async def _reset_connection(self) -> None:
        """Reset the Modbus connection after repeated errors.

        Used when flush() alone is not sufficient to recover. This is a
        heavier-weight operation that closes and reopens the TCP connection.

        Per ModbusLink 1.4.2 best practices:
        1. First try flush() to clear stale data (lighter)
        2. Only reset connection after multiple consecutive errors
        """
        log_debug(_LOGGER, "_reset_connection", "Resetting connection")
        with contextlib.suppress(OSError):
            await self._transport.close()
        # Delay to ensure TCP buffers clear and stale responses are discarded
        await asyncio.sleep(1.0)
        try:
            await self._transport.open()
            log_debug(_LOGGER, "_reset_connection", "Connection reset successful")
        except OSError as e:
            log_warning(_LOGGER, "_reset_connection", "Reconnect failed", error=e)
            raise

    async def get_mac_address(self) -> str:
        """Get mac address from ip/hostname with improved retry logic."""
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

                mac_address = getmac.get_mac_address(hostname=self._host, network_request=True)

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
                    delay = min(2**attempt + random.uniform(0, 1), 10)  # noqa: S311
                    log_debug(
                        _LOGGER,
                        "get_mac_address",
                        f"MAC retrieval attempt {attempt + 1} failed, retrying",
                        delay_s=f"{delay:.1f}",
                    )
                    await asyncio.sleep(delay)

            except OSError as e:
                # OSError covers network-related errors from getmac
                log_debug(
                    _LOGGER,
                    "get_mac_address",
                    f"MAC retrieval attempt {attempt + 1} failed",
                    error=e,
                )
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    delay = min(2**attempt + random.uniform(0, 1), 10)  # noqa: S311
                    await asyncio.sleep(delay)

        log_debug(_LOGGER, "get_mac_address", "MAC address not found after all attempts")
        # Return a fallback unique identifier based on host:port
        fallback_id = f"{self._host.replace('.', '')}_{self._port}"
        log_debug(_LOGGER, "get_mac_address", "Using fallback ID", fallback_id=fallback_id)
        return fallback_id

    async def check_port(self) -> bool:
        """Check if port is available."""
        # Use configured timeout for socket check
        sock_timeout = self._timeout
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
            # Force IPv4 (AF_INET) to avoid dual-stack timeout issues
            # Some devices only support IPv4, and dual-stack DNS can cause
            # timeouts when IPv6 is tried first but not supported
            _reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self._host,
                    self._port,
                    family=socket.AF_INET,
                ),
                timeout=sock_timeout,
            )

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
        else:
            return True

    async def _read_batch(self, start_address: int, count: int) -> list[int]:
        """Read a batch of consecutive registers with layered error handling.

        Implements retry logic for transient errors (connection, timeout)
        while failing fast on protocol/data errors per ModbusLink best practices.

        Args:
            start_address: Starting register address
            count: Number of registers to read

        Returns:
            List of register values

        Raises:
            SinapsiConnectionError: After all retries exhausted for transient errors
            SinapsiModbusError: For non-retriable protocol/data errors

        """
        last_error: Exception | None = None

        for attempt in range(BATCH_MAX_RETRIES):
            try:
                return await self._client.read_holding_registers(
                    slave_id=self._device_id,
                    start_address=start_address,
                    quantity=count,
                )

            except ModbusConnectionError as e:
                # Transient - retry with backoff
                last_error = e
                if attempt < BATCH_MAX_RETRIES - 1:
                    log_warning(
                        _LOGGER,
                        "_read_batch",
                        "Connection error, retrying",
                        attempt=attempt + 1,
                        address=start_address,
                    )
                    await asyncio.sleep(BATCH_RETRY_DELAY_CONNECTION)
                continue

            except ModbusTimeoutError as e:
                # Transient - flush buffer and retry (per ModbusLink 1.4.2 pattern)
                last_error = e
                self._protocol_errors_this_cycle += 1
                if attempt < BATCH_MAX_RETRIES - 1:
                    log_warning(
                        _LOGGER,
                        "_read_batch",
                        "Timeout error, flushing buffer and retrying",
                        attempt=attempt + 1,
                        address=start_address,
                        protocol_errors=self._protocol_errors_this_cycle,
                    )
                    # Flush buffer to clear any late responses
                    await self._flush_buffer()
                    # Reset connection if too many consecutive errors
                    if self._protocol_errors_this_cycle >= MAX_PROTOCOL_ERRORS_PER_CYCLE:
                        await self._reset_connection()
                    await asyncio.sleep(BATCH_RETRY_DELAY_TIMEOUT)
                continue

            except InvalidReplyError as e:
                # Transaction ID mismatch - flush buffer first (lighter recovery)
                last_error = e
                self._protocol_errors_this_cycle += 1
                if attempt < BATCH_MAX_RETRIES - 1:
                    log_warning(
                        _LOGGER,
                        "_read_batch",
                        "Protocol error (Transaction ID mismatch), flushing buffer",
                        attempt=attempt + 1,
                        address=start_address,
                        protocol_errors=self._protocol_errors_this_cycle,
                    )
                    # Flush buffer to clear stale responses
                    await self._flush_buffer()
                    # Reset connection if too many consecutive errors
                    if self._protocol_errors_this_cycle >= MAX_PROTOCOL_ERRORS_PER_CYCLE:
                        await self._reset_connection()
                    await asyncio.sleep(BATCH_RETRY_DELAY_PROTOCOL)
                continue

            except CrcError as e:
                # CRC errors - flush buffer first, then reset if needed
                last_error = e
                self._protocol_errors_this_cycle += 1
                if attempt < BATCH_MAX_RETRIES - 1:
                    log_warning(
                        _LOGGER,
                        "_read_batch",
                        "CRC error, flushing buffer",
                        attempt=attempt + 1,
                        address=start_address,
                        protocol_errors=self._protocol_errors_this_cycle,
                    )
                    # Flush buffer to clear corrupted data
                    await self._flush_buffer()
                    # Reset connection if too many consecutive errors
                    if self._protocol_errors_this_cycle >= MAX_PROTOCOL_ERRORS_PER_CYCLE:
                        await self._reset_connection()
                    await asyncio.sleep(BATCH_RETRY_DELAY_PROTOCOL)
                continue

            except ModbusException as e:
                # Modbus protocol errors - fail immediately
                log_error(
                    _LOGGER,
                    "_read_batch",
                    "Modbus protocol error",
                    address=start_address,
                    error=e,
                )
                raise SinapsiModbusError(
                    f"Modbus error at address {start_address}: {e}",
                    start_address,
                    "read_batch",
                ) from e

            except ModbusLinkError as e:
                # Catch-all for any other ModbusLink errors
                log_error(
                    _LOGGER,
                    "_read_batch",
                    "Unexpected ModbusLink error",
                    address=start_address,
                    error=e,
                )
                raise SinapsiModbusError(
                    f"ModbusLink error at address {start_address}: {e}",
                    start_address,
                    "read_batch",
                ) from e

        # All retries exhausted
        self._connection_healthy = False
        raise SinapsiConnectionError(
            f"Batch read failed after {BATCH_MAX_RETRIES} attempts: {last_error}",
            self._host,
            self._port,
        ) from last_error

    def _extract_uint16(self, registers: list[int], offset: int) -> int:
        """Extract uint16 value from register batch.

        Args:
            registers: List of register values from batch read
            offset: Offset within the batch

        Returns:
            16-bit unsigned integer value

        """
        return registers[offset]

    def _extract_uint32(self, registers: list[int], offset: int) -> int:
        """Extract uint32 value (big-endian) from register batch.

        Args:
            registers: List of register values from batch read
            offset: Offset within the batch (points to high word)

        Returns:
            32-bit unsigned integer value

        """
        return (registers[offset] << 16) | registers[offset + 1]

    def _extract_sensor_value(self, batches: list[list[int]], sensor_key: str) -> float:
        """Extract sensor value from batch results.

        Args:
            batches: List of batch results from parallel reads
            sensor_key: Sensor key to look up in SENSOR_MAP

        Returns:
            Raw sensor value as float

        Raises:
            ValueError: If sensor has unknown register type

        """
        batch_idx, offset, reg_type = SENSOR_MAP[sensor_key]
        registers = batches[batch_idx]

        if reg_type == "uint16":
            return float(self._extract_uint16(registers, offset))
        if reg_type == "uint32":
            return float(self._extract_uint32(registers, offset))
        raise ValueError(f"Unknown register type: {reg_type}")

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
            return unix_timestamp_to_iso8601_local_tz(value + self.data["tempo_residuo_distacco"])

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

    async def async_get_data(self) -> bool:
        """Read data using client context manager.

        Uses ModbusLink's context manager for automatic connection handling.
        The context manager opens the transport on entry and closes on exit.

        Returns:
            True if data collection succeeded

        Raises:
            SinapsiConnectionError: If device is not reachable or connection fails
            SinapsiModbusError: If Modbus operations fail

        """
        try:
            # Pre-check if device is reachable
            if not await self.check_port():
                self._connection_healthy = False
                raise SinapsiConnectionError(
                    f"Device not active on {self._host}:{self._port}",
                    self._host,
                    self._port,
                )

            # Get MAC address BEFORE opening Modbus connection (only first time)
            # This prevents connection timeout during MAC retrieval on VPN/slow networks
            if not self._uid:
                if self._skip_mac_detection:
                    # Skip MAC retrieval - use host-based ID directly (faster for VPN)
                    self._uid = f"{self._host.replace('.', '')}_{self._port}"
                    log_debug(
                        _LOGGER,
                        "async_get_data",
                        "Using host-based ID (MAC detection skipped)",
                        uid=self._uid,
                    )
                else:
                    self._uid = await self.get_mac_address()
                self.data["sn"] = self._uid

            log_debug(
                _LOGGER,
                "async_get_data",
                "Start data collection",
                host=self._host,
                port=self._port,
            )

            # Context manager on CLIENT (opens/closes transport automatically)
            async with self._client:
                result = await self.read_modbus_alfa()

                if result:
                    log_debug(_LOGGER, "async_get_data", "Data collection completed")
                    self._connection_healthy = True
                    self._last_successful_read = time.time()
                    return True

                log_debug(_LOGGER, "async_get_data", "Data validation: invalid")
                return False

        except (ModbusConnectionError, ModbusTimeoutError) as connect_error:
            self._connection_healthy = False
            raise SinapsiConnectionError(
                f"Connection failed: {connect_error}", self._host, self._port
            ) from connect_error

    def _check_protocol_error_limit(self) -> None:
        """Check if protocol errors exceed limit and abort early if so.

        Raises:
            SinapsiModbusError: If too many protocol errors occurred this cycle

        """
        if self._protocol_errors_this_cycle >= MAX_PROTOCOL_ERRORS_PER_CYCLE:
            log_warning(
                _LOGGER,
                "read_modbus_alfa",
                "Aborting cycle early due to repeated protocol errors",
                protocol_errors=self._protocol_errors_this_cycle,
                max_allowed=MAX_PROTOCOL_ERRORS_PER_CYCLE,
            )
            raise SinapsiModbusError(
                f"Too many protocol errors ({self._protocol_errors_this_cycle}), "
                "aborting to avoid cascade delays"
            )

    async def read_modbus_alfa(self) -> bool:
        """Read all Modbus registers using sequential batch operations.

        Reads registers in 5 batches instead of 20 individual reads (~75% fewer requests).
        Batches are read sequentially to avoid Transaction ID mismatch errors.

        Returns:
            True if all reads succeeded

        Raises:
            SinapsiModbusError: If any batch read fails

        """
        # Reset protocol error counter for this cycle
        self._protocol_errors_this_cycle = 0

        try:
            # Read all batches sequentially (parallel causes Transaction ID mismatches)
            batches: list[list[int]] = []
            for start, count in REGISTER_BATCHES:
                # Check for early abort if too many protocol errors
                self._check_protocol_error_limit()
                result = await self._read_batch(start, count)
                batches.append(result)

            # Extract and process all sensor values
            for sensor in SENSOR_ENTITIES:
                sensor_def = cast(dict[str, Any], sensor)
                if sensor_def["modbus_type"] == "calcolato":
                    continue  # Skip calculated sensors

                key = str(sensor_def["key"])
                raw_value = self._extract_sensor_value(batches, key)
                processed_value = self._process_sensor_value(raw_value, sensor_def)
                self.data[key] = processed_value

                log_debug(
                    _LOGGER,
                    "read_modbus_alfa",
                    "Sensor processed",
                    sensor=key,
                    address=sensor_def["modbus_addr"],
                    value=processed_value,
                )

            # Calculate derived values
            self._calculate_derived_values()
        except Exception as error:
            log_error(_LOGGER, "read_modbus_alfa", "Failed to read modbus data", error=error)
            raise SinapsiModbusError(f"Failed to read modbus data: {error}") from error
        else:
            return True
