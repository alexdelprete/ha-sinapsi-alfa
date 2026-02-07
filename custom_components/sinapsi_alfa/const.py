"""Constants for Sinapsi Alfa.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from modbuslink import __version__ as MODBUSLINK_VERSION

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower

# Base component constants
NAME = "Sinapsi Alfa"
DOMAIN = "sinapsi_alfa"
VERSION = "1.2.12"
ATTRIBUTION = "by @alexdelprete"
ISSUE_URL = "https://github.com/alexdelprete/ha-sinapsi-alfa/issues"

# Configuration and options
CONF_NAME = "name"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TIMEOUT = "timeout"
CONF_SKIP_MAC_DETECTION = "skip_mac_detection"
DEFAULT_NAME = "Alfa"
DEFAULT_PORT = 502
DEFAULT_DEVICE_ID = 1
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 600
DEFAULT_TIMEOUT = 10
MIN_TIMEOUT = 5
MAX_TIMEOUT = 60
DEFAULT_SKIP_MAC_DETECTION = False
MANUFACTURER = "Sinapsi"
MODEL = "Alfa"

# Repair notification options
CONF_ENABLE_REPAIR_NOTIFICATION = "enable_repair_notification"
CONF_FAILURES_THRESHOLD = "failures_threshold"
CONF_RECOVERY_SCRIPT = "recovery_script"
DEFAULT_ENABLE_REPAIR_NOTIFICATION = True
DEFAULT_FAILURES_THRESHOLD = 3
DEFAULT_RECOVERY_SCRIPT = ""
MIN_FAILURES_THRESHOLD = 1
MAX_FAILURES_THRESHOLD = 10

# Validation constants
MIN_PORT = 1
MAX_PORT = 65535

# API Constants
DEFAULT_SENSOR_VALUE = 0.0
MAX_RETRY_ATTEMPTS = 5
INVALID_DISTACCO_VALUE = 65535
MAX_EVENT_VALUE = 4294967294

# Batch read configuration: (start_address, count)
# Groups consecutive registers to minimize Modbus requests
# 5 batches instead of 20 individual reads = ~75% reduction in requests
REGISTER_BATCHES: list[tuple[int, int]] = [
    (2, 18),  # Batch 0: Power/energy basics (addr 2-19)
    (30, 36),  # Batch 1: Daily energy F1-F6 (addr 30-65)
    (203, 1),  # Batch 2: Time band (addr 203)
    (780, 3),  # Batch 3: Event data (addr 780-782)
    (921, 5),  # Batch 4: Production (addr 921-925)
]

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME} - Version {VERSION} (modbuslink {MODBUSLINK_VERSION})
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
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "uint16",
        "modbus_addr": 2,
    },
    {
        "name": "Potenza Prelevata Media 15m",
        "key": "potenza_prelevata_media_15m",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "uint16",
        "modbus_addr": 9,
    },
    {
        "name": "Potenza Immessa",
        "key": "potenza_immessa",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "modbus_type": "uint16",
        "modbus_addr": 12,
    },
    {
        "name": "Potenza Immessa Media 15m",
        "key": "potenza_immessa_media_15m",
        "icon": "mdi:transmission-tower-import",
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
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 5,
    },
    {
        "name": "Energia Immessa",
        "key": "energia_immessa",
        "icon": "mdi:transmission-tower-import",
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
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 30,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Prelevata Giornaliera F2",
        "key": "energia_prelevata_giornaliera_f2",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 32,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Prelevata Giornaliera F3",
        "key": "energia_prelevata_giornaliera_f3",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 34,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Prelevata Giornaliera F4",
        "key": "energia_prelevata_giornaliera_f4",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 36,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Prelevata Giornaliera F5",
        "key": "energia_prelevata_giornaliera_f5",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 38,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Prelevata Giornaliera F6",
        "key": "energia_prelevata_giornaliera_f6",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 40,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Immessa Giornaliera F1",
        "key": "energia_immessa_giornaliera_f1",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 54,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Immessa Giornaliera F2",
        "key": "energia_immessa_giornaliera_f2",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 56,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Immessa Giornaliera F3",
        "key": "energia_immessa_giornaliera_f3",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 58,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Immessa Giornaliera F4",
        "key": "energia_immessa_giornaliera_f4",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 60,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Immessa Giornaliera F5",
        "key": "energia_immessa_giornaliera_f5",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 62,
        "disabled_by_default": True,
    },
    {
        "name": "Energia Immessa Giornaliera F6",
        "key": "energia_immessa_giornaliera_f6",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "modbus_type": "uint32",
        "modbus_addr": 64,
        "disabled_by_default": True,
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
