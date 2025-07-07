"""Constants for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower

# Base component constants
NAME = "Sinapsi Alfa"
DOMAIN = "sinapsi_alfa"
ATTRIBUTION = "by @alexdelprete"
ISSUE_URL = "https://github.com/alexdelprete/ha-sinapsi-alfa/issues"

# Configuration and options
CONF_NAME = "name"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_NAME = "Alfa"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
CONN_TIMEOUT = 5
MANUFACTURER = "Sinapsi"
MODEL = "Alfa"

# API Constants
DEFAULT_SENSOR_VALUE = 0.0
MAX_RETRY_ATTEMPTS = 10
SOCKET_TIMEOUT = 3.0
INVALID_DISTACCO_VALUE = 65535
MAX_EVENT_VALUE = 4294967294
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
{ATTRIBUTION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Sensor definitions
SENSOR_ENTITIES = [
    {
        "name": "Potenza Prelevata",
        "key": "potenza_prelevata",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "uint16",
        "modbus_addr": 2,
    },
    {
        "name": "Potenza Prelevata Media 15m",
        "key": "potenza_prelevata_media_15m",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "uint16",
        "modbus_addr": 9,
    },
    {
        "name": "Potenza Immessa",
        "key": "potenza_immessa",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "uint16",
        "modbus_addr": 12,
    },
    {
        "name": "Potenza Immessa Media 15m",
        "key": "potenza_immessa_media_15m",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "uint16",
        "modbus_addr": 19,
    },
    {
        "name": "Potenza Prodotta",
        "key": "potenza_prodotta",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "uint16",
        "modbus_addr": 921,
    },
    {
        "name": "Energia Prelevata",
        "key": "energia_prelevata",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 5,
    },
    {
        "name": "Energia Immessa",
        "key": "energia_immessa",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 15,
    },
    {
        "name": "Energia Prodotta",
        "key": "energia_prodotta",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 924,
    },
    {
        "name": "Energia Prelevata Giornaliera F1",
        "key": "energia_prelevata_giornaliera_f1",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 30,
    },
    {
        "name": "Energia Prelevata Giornaliera F2",
        "key": "energia_prelevata_giornaliera_f2",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 32,
    },
    {
        "name": "Energia Prelevata Giornaliera F3",
        "key": "energia_prelevata_giornaliera_f3",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 34,
    },
    {
        "name": "Energia Prelevata Giornaliera F4",
        "key": "energia_prelevata_giornaliera_f4",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 36,
    },
    {
        "name": "Energia Prelevata Giornaliera F5",
        "key": "energia_prelevata_giornaliera_f5",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 38,
    },
    {
        "name": "Energia Prelevata Giornaliera F6",
        "key": "energia_prelevata_giornaliera_f6",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 40,
    },
    {
        "name": "Energia Immessa Giornaliera F1",
        "key": "energia_immessa_giornaliera_f1",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 54,
    },
    {
        "name": "Energia Immessa Giornaliera F2",
        "key": "energia_immessa_giornaliera_f2",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 56,
    },
    {
        "name": "Energia Immessa Giornaliera F3",
        "key": "energia_immessa_giornaliera_f3",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 58,
    },
    {
        "name": "Energia Immessa Giornaliera F4",
        "key": "energia_immessa_giornaliera_f4",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 60,
    },
    {
        "name": "Energia Immessa Giornaliera F5",
        "key": "energia_immessa_giornaliera_f5",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 62,
    },
    {
        "name": "Energia Immessa Giornaliera F6",
        "key": "energia_immessa_giornaliera_f6",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 64,
    },
    {
        "name": "Fascia Oraria Attuale",
        "key": "fascia_oraria_attuale",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "modbus_type": "uint16",
        "modbus_addr": 203,
    },
    {
        "name": "Tempo Residuo Distacco",
        "key": "tempo_residuo_distacco",
        "icon": "mdi:timer-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "modbus_type": "uint16",
        "modbus_addr": 782,
    },
    {
        "name": "Data Evento",
        "key": "data_evento",
        "icon": "mdi:calendar-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "modbus_type": "uint32",
        "modbus_addr": 780,
    },
    {
        "name": "Potenza Consumata",
        "key": "potenza_consumata",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "calcolato",
        "modbus_addr": None,
    },
    {
        "name": "Potenza Auto Consumata",
        "key": "potenza_auto_consumata",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "calcolato",
        "modbus_addr": None,
    },
    {
        "name": "Energia Consumata",
        "key": "energia_consumata",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "calcolato",
        "modbus_addr": None,
    },
    {
        "name": "Energia Auto Consumata",
        "key": "energia_auto_consumata",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "calcolato",
        "modbus_addr": None,
    },
]
