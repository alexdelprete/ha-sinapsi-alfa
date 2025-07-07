"""API Platform for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

import logging
import socket
import threading

from getmac import getmac
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ConnectionException, ModbusException

from .const import DEFAULT_SLAVE_ID, MANUFACTURER, MODEL, SENSOR_ENTITIES
from .helpers import unix_timestamp_to_iso8601_local_tz

# from pymodbus.payload import BinaryPayloadDecoder
from .modbuspayload import BinaryPayloadDecoder

_LOGGER = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Empty Error Class."""


class ModbusError(Exception):
    """Empty Error Class."""


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
        self._slave_id = DEFAULT_SLAVE_ID
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
        mac_address = None
        i = 0
        # we want to ensure a mac address if found, sometimes it takes more than 1 try
        while not mac_address and i < 10:
            if self.check_port():
                _LOGGER.debug(
                    f"Get_Mac_Address (SUCCESS): port open on {self._host}:{self._port}"
                )
            else:
                _LOGGER.debug(
                    f"Get_Mac_Address (ERROR): port not available on {self._host}:{self._port}"
                )
            # Get MAC address from the ARP cache using the hostname
            mac_address = getmac.get_mac_address(
                hostname=self._host, network_request=False
            )
            i = i + 1
        if mac_address is not None:
            # Remove colons and convert to uppercase
            mac_address = mac_address.replace(":", "").upper()
            _LOGGER.debug(f"Get_Mac_Address (SUCCESS): found mac address {mac_address}")
        else:
            mac_address = ""
            _LOGGER.debug(
                f"Get_Mac_Address (ERROR): mac address not found! {mac_address}"
            )
        return mac_address

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

        try:
            with self._lock:
                return self._client.read_holding_registers(
                    address=address, count=count, slave=self._slave_id
                )
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
                    f"Start Get data (Host: {self._host} - Port: {self._port})",
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
                # if reg_type is calcolato, calculate the values
                if reg_type == "calcolato":
                    self.data["potenza_auto_consumata"] = (
                        self.data["potenza_prodotta"] - self.data["potenza_immessa"]
                    )
                    self.data["potenza_consumata"] = (
                        self.data["potenza_auto_consumata"]
                        + self.data["potenza_prelevata"]
                    )

                    self.data["energia_auto_consumata"] = (
                        self.data["energia_prodotta"] - self.data["energia_immessa"]
                    )
                    self.data["energia_consumata"] = (
                        self.data["energia_auto_consumata"]
                        + self.data["energia_prelevata"]
                    )
                else:
                    read_data = self.read_holding_registers(
                        address=reg_addr, count=reg_count
                    )
                    # No connection errors, we can start scraping registers
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        read_data.registers, byteorder=Endian.BIG
                    )

                    # decode the register based on type
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
                        value = round(float(value) / 1000, 2)
                    # if not power/energy type, it's an integer
                    else:
                        value = int(value)

                    # if distacco is 65535 set it to 0
                    if reg_key == "tempo_residuo_distacco":
                        if value == 65535:
                            value = 0

                    # if data_evento is > 4294967294 then no event
                    if reg_key == "data_evento":
                        if value > 4294967294:
                            value = "None"
                        else:
                            # convert timestamp to ISO8601
                            value = unix_timestamp_to_iso8601_local_tz(
                                value + self.data["tempo_residuo_distacco"]
                            )
                    # Prepending "F" to fascia oraria for consistency
                    if reg_key == "fascia_oraria_attuale":
                        value = f"F{value}"

                    # Store the value in the data dictionary
                    self.data[reg_key] = value

                    _LOGGER.debug(f"(read_modbus_alfa) Data: {self.data[reg_key]}")
        except Exception as modbus_error:
            _LOGGER.debug(f"(read_modbus_alfa): failed with error: {modbus_error}")
            result = False
            raise ModbusError() from modbus_error
        return result
