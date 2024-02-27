"""API Platform for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import logging
import socket
import threading

import getmac
from homeassistant.components.sensor import SensorDeviceClass
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.payload import BinaryPayloadDecoder

from .const import MANUFACTURER, MODEL, SENSOR_ENTITIES

_LOGGER = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Empty Error Class."""


class ModbusError(Exception):
    """Empty Error Class."""


class SinapsiAlfaAPI:
    """Thread safe wrapper class for pymodbus."""

    def __init__(
        self,
        hass,
        name,
        host,
        port,
        scan_interval,
    ):
        """Initialize the Modbus API Client."""
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._update_interval = scan_interval
        # Ensure ModBus Timeout is 1s less than scan_interval
        # https://github.com/binsentsu/home-assistant-solaredge-modbus/pull/183
        self._timeout = self._update_interval - 1
        self._client = ModbusTcpClient(
            host=self._host, port=self._port, timeout=self._timeout
        )
        self._lock = threading.Lock()
        self._uid = self.get_mac_address()
        self._sensors = []
        self.data = {}
        # Initialize ModBus data structure before first read
        self.data["potenza_prelevata"] = 1
        self.data["potenza_immessa"] = 1
        self.data["potenza_prodotta"] = 1
        self.data["potenza_consumata"] = 1
        self.data["potenza_auto_consumata"] = 1
        self.data["energia_prelevata"] = 1
        self.data["energia_immessa"] = 1
        self.data["energia_prodotta"] = 1
        self.data["energia_consumata"] = 1
        self.data["energia_auto_consumata"] = 1
        self.data["energia_prelevata_giornaliera_f1"] = 1
        self.data["energia_prelevata_giornaliera_f2"] = 1
        self.data["energia_prelevata_giornaliera_f3"] = 1
        self.data["energia_prelevata_giornaliera_f4"] = 1
        self.data["energia_prelevata_giornaliera_f5"] = 1
        self.data["energia_prelevata_giornaliera_f6"] = 1
        self.data["energia_immessa_giornaliera_f1"] = 1
        self.data["energia_immessa_giornaliera_f2"] = 1
        self.data["energia_immessa_giornaliera_f3"] = 1
        self.data["energia_immessa_giornaliera_f4"] = 1
        self.data["energia_immessa_giornaliera_f5"] = 1
        self.data["energia_immessa_giornaliera_f6"] = 1
        self.data["fascia_oraria_attuale"] = 1
        self.data["data_evento"] = 1
        self.data["tempo_residuo_distacco"] = 1
        # custom fields to reuse code structure
        self.data["manufact"] = MANUFACTURER
        self.data["model"] = MODEL
        self.data["sn"] = self._uid

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

    def get_mac_address(self) -> str:
        """Get mac address from ip/hostname."""
        try:
            # Get MAC address from the ARP cache using the hostname
            mac_address_with_colons = getmac.get_mac_address(hostname=self._host)
            # Remove colons and convert to uppercase
            mac_address = mac_address_with_colons.replace(":", "").upper()
            return mac_address
        except Exception as e:
            return f"(get_mac_address) ERROR: {e}"

    def check_port(self) -> bool:
        """Check if port is available."""
        with self._lock:
            sock_timeout = float(3)
            _LOGGER.debug(
                f"Check_Port: opening socket on {self._host}:{self._port} with a {sock_timeout}s timeout."
            )
            socket.setdefaulttimeout(sock_timeout)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_res = sock.connect_ex((self._host, self._port))
            is_open = sock_res == 0  # True if open, False if not
            if is_open:
                sock.shutdown(socket.SHUT_RDWR)
                _LOGGER.debug(
                    f"Check_Port (SUCCESS): port open on {self._host}:{self._port}"
                )
            else:
                _LOGGER.debug(
                    f"Check_Port (ERROR): port not available on {self._host}:{self._port} - error: {sock_res}"
                )
            sock.close()
        return is_open

    def close(self):
        """Disconnect client."""
        try:
            if self._client.is_socket_open():
                _LOGGER.debug("Closing Modbus TCP connection")
                with self._lock:
                    self._client.close()
                    return True
            else:
                _LOGGER.debug("Modbus TCP connection already closed")
        except ConnectionException as connect_error:
            _LOGGER.debug(f"Close Connection connect_error: {connect_error}")
            raise ConnectionError() from connect_error

    def connect(self):
        """Connect client."""
        _LOGGER.debug(
            f"API Client connect to IP: {self._host} port: {self._port} timeout: {self._timeout}"
        )
        if self.check_port():
            _LOGGER.debug("Inverter ready for Modbus TCP connection")
            try:
                with self._lock:
                    self._client.connect()
                if not self._client.connected:
                    raise ConnectionError(
                        f"Failed to connect to {self._host}:{self._port} timeout: {self._timeout}"
                    )
                else:
                    _LOGGER.debug("Modbus TCP Client connected")
                    return True
            except ModbusException:
                raise ConnectionError(
                    f"Failed to connect to {self._host}:{self._port} timeout: {self._timeout}"
                )
        else:
            _LOGGER.debug("Inverter not ready for Modbus TCP connection")
            raise ConnectionError(f"Inverter not active on {self._host}:{self._port}")

    def read_holding_registers(self, address, count):
        """Read holding registers."""
        kwargs = {}
        try:
            with self._lock:
                return self._client.read_holding_registers(address, count, **kwargs)
        except ConnectionException as connect_error:
            _LOGGER.debug(f"Read Holding Registers connect_error: {connect_error}")
            raise ConnectionError() from connect_error
        except ModbusException as modbus_error:
            _LOGGER.debug(f"Read Holding Registers modbus_error: {modbus_error}")
            raise ModbusError() from modbus_error

    async def async_get_data(self):
        """Read Data Function."""

        try:
            if self.connect():
                _LOGGER.debug(
                    "Start Get data (Host: %s - Port: %s)",
                    self._host,
                    self._port,
                )
                # HA way to call a sync function from async function
                # https://developers.home-assistant.io/docs/asyncio_working_with_async?#calling-sync-functions-from-async
                result = await self._hass.async_add_executor_job(self.read_modbus_alfa)
                self.close()
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
            raise ConnectionError() from connect_error
        except ModbusException as modbus_error:
            _LOGGER.debug(f"Async Get Data modbus_error: {modbus_error}")
            raise ModbusError() from modbus_error

    def read_modbus_alfa(self):
        """Read Alfa modbus registers."""
        try:
            result = True
            for sensor in SENSOR_ENTITIES:
                reg_key = sensor["key"]
                reg_dev_class = sensor["device_class"]
                reg_type = sensor["modbus_type"]
                reg_addr = sensor["modbus_addr"]
                reg_count = 1 if reg_type == "uint16" else 2
                _LOGGER.debug(
                    f"(read_modbus_alfa) Key: {reg_key} Addr: {reg_addr} Type: {reg_type} DevClass: {reg_dev_class}"
                )
                if reg_type == "calculated":
                    self.data["potenza_consumata"] = (
                        self.data["potenza_prodotta"]
                        - self.data["potenza_immessa"]
                        + self.data["potenza_prelevata"]
                    )
                    self.data["potenza_auto_consumata"] = (
                        self.data["potenza_prodotta"] - self.data["potenza_immessa"]
                    )

                    self.data["energia_consumata"] = (
                        self.data["energia_prodotta"]
                        - self.data["energia_immessa"]
                        + self.data["energia_prelevata"]
                    )
                    self.data["energia_auto_consumata"] = (
                        self.data["energia_prodotta"] - self.data["energia_immessa"]
                    )
                else:
                    read_data = self.read_holding_registers(
                        address=reg_addr, count=reg_count
                    )
                    # No connection errors, we can start scraping registers
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        read_data.registers, byteorder=Endian.BIG
                    )
                    if reg_type == "uint16":
                        value = round(float(decoder.decode_16bit_uint()), 2)
                    elif reg_type == "uint32":
                        value = round(float(decoder.decode_32bit_uint()), 2)
                    _LOGGER.debug(f"(read_modbus_alfa) Raw Value: {value}")
                    # Alfa provides power/energy data in W/Wh, we want kW/kWh
                    if reg_dev_class in [
                        SensorDeviceClass.ENERGY,
                        SensorDeviceClass.POWER,
                    ]:
                        value = round(float(value / 1000), 2)
                    else:
                        value = int(value)
                    self.data[reg_key] = value
                    _LOGGER.debug(f"(read_modbus_alfa) Data: {self.data[reg_key]}")
        except Exception as modbus_error:
            _LOGGER.debug(f"(read_modbus_alfa): failed with error: {modbus_error}")
            result = False
            raise ModbusError() from modbus_error
        return result
