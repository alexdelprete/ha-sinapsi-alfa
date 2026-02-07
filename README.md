# HA Custom Integration: Alfa by Sinapsi energy monitoring device

[![GitHub Release][releases-shield]][releases]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Community Forum][forum-shield]][forum]

[![Tests][tests-shield]][tests]
[![Code Coverage][coverage-shield]][coverage]
[![Downloads][downloads-shield]][downloads]

_This project is not endorsed by, directly affiliated with, maintained,
authorized, or sponsored by Sinapsi_

## Introduction

HA Custom Component to integrate data from [Sinapsi Alfa][alfa] device.
Tested on my Alfa to monitor the power/energy consumption and photovoltaic
power/energy production directly from the energy provider's OpenMeter 2.0.

![Alfa Device][img-device]

Alfa is a great product, it provides official measurements, and it provides
local API to get the data (for now it's through ModBus).

So finally here we are with the first official version of the HA custom
integration for Alfa devices. :)

## Features

- Installation/Configuration through Config Flow UI
- Sensor entities for all data provided by the device
- **Translated sensor names**: Sensor names displayed in your Home Assistant
  language (supports German, English, Spanish, Estonian, Finnish, French,
  Italian, Norwegian, Portuguese, and Swedish)
- **Options flow**: Adjust polling interval, connection timeout, and repair
  notification settings at runtime
- **Reconfigure flow**: Change device name, host, port, and skip MAC detection
- **Repair notifications**: Connection issues are surfaced in Home Assistant's
  repair system with configurable threshold
- **Recovery notifications**: Detailed timing info (downtime, script execution)
  when device recovers
- **Device triggers**: Automate based on device connection events (unreachable,
  not responding, recovered)
- **Recovery script**: Optionally execute a script when connection failures
  reach the threshold
- **Diagnostics**: Downloadable diagnostics file for troubleshooting
- All changes apply immediately without Home Assistant restart

## Technical Architecture

This integration uses a fully async Modbus implementation via `ModbusLink`
to communicate with the Sinapsi Alfa device:

- **Async I/O**: All Modbus operations are fully async, preventing Home
  Assistant event loop blocking
- **Connection Management**: Connections use configurable timeouts with
  automatic retry on failure
- **Protocol Error Recovery**: Early abort when multiple protocol errors
  occur to prevent cascade delays
- **Graceful Error Handling**: Custom exceptions (`SinapsiConnectionError`,
  `SinapsiModbusError`) provide clear error context
- **Repair Notifications**: Connection issues are surfaced in Home Assistant's
  repair system after repeated failures

## Important: Modbus Integration Conflict

The Sinapsi Alfa device only supports **one Modbus TCP client at a time**.

Many users have the Sinapsi-provided YAML package
(`alfa-ha-modbus-configuration.yaml`) installed, which uses Home Assistant's
built-in Modbus integration. If you install this custom integration without
removing that package, both integrations will try to connect to the same
device, causing connection failures.

**Before installing this integration:**

1. Remove or rename the Sinapsi YAML package file
   (`alfa-ha-modbus-configuration.yaml`) from your `packages` folder
2. Restart Home Assistant
3. Then proceed with installing this integration

The integration will detect this conflict and show a clear error message if
the built-in Modbus integration is still configured for the same device.

## Installation through HACS

This integration is available in [HACS] official repository.
Click this button to open HA directly on the integration page so you can
easily install it:

[![Quick installation link][hacs-badge]][my-hacs]

1. Either click the button above, or navigate to HACS in Home Assistant and:
   - 'Explore & Download Repositories'
   - Search for 'Alfa by Sinapsi'
   - Download
1. Restart Home Assistant
1. Go to Settings > Devices and Services > Add Integration
1. Search for and select 'Alfa by Sinapsi' (if the integration is not found,
   do a hard-refresh (ctrl+F5) in the browser)
1. Proceed with the configuration

## Manual Installation

Download the source code archive from the release page. Unpack the archive
and copy the contents of custom_components folder to your home-assistant
config/custom_components folder. Restart Home Assistant, and then the
integration can be added and configured through the native integration
setup UI. If you don't see it in the native integrations list, press
ctrl-F5 to refresh the browser while you're on that page and retry.

## Configuration

Configuration is done via config flow right after adding the integration.

### Initial Setup

During initial setup, you configure all settings:

- **Device name**: Custom name for the device (used as prefix for sensor names)
- **IP/Hostname**: IP address or hostname of the Alfa device
- **TCP port**: Modbus TCP port (default: 502)
- **Polling interval**: How often to read data from the device (30-600 seconds)
- **Connection timeout**: How long to wait for device response (5-60 seconds)
- **Skip MAC detection**: Enable for VPN connections (uses host-based ID)

![Config Flow][img-config]

### Runtime Options

After installation, you can adjust runtime settings without restart:

1. Go to **Settings** > **Devices & Services** > **Alfa by Sinapsi**
1. Click **Configure** to open the options dialog
1. Adjust the available options:
   - **Recovery script**: Script to execute when failure threshold is reached
   - **Enable repair notifications**: Toggle repair issue creation on/off
   - **Failures before notification**: Number of failures before creating
     repair issue (1-10)
   - **Polling interval**: How often to read data (30-600 seconds)
   - **Connection timeout**: How long to wait for response (5-60 seconds)
1. Click **Submit** - changes apply immediately

### Reconfiguring Connection Settings

To change the device name, host, port, or skip MAC detection:

1. Go to **Settings** > **Devices & Services** > **Alfa by Sinapsi**
1. Click the **three-dot menu** (⋮) on the integration card
1. Select **Reconfigure**
1. Update the settings and click **Submit**

Note: Entity IDs are based on the device serial number, so changing the
device name or host will not affect your historical data or automations.

## Sensor View

![Sensors][img-sensors]

## Device Triggers

The integration provides device triggers that allow you to create automations
based on device connection events. These triggers fire when the Sinapsi Alfa
device experiences connectivity issues or recovers from them.

### Available Triggers

| Trigger | Description |
|---------|-------------|
| **Device unreachable** | Fires when the device cannot be reached (network/connection issue) |
| **Device not responding** | Fires when Modbus communication fails |
| **Device recovered** | Fires when the device starts responding again after a failure |

### How to Use Device Triggers

1. Go to **Settings > Automations & Scenes > Create Automation**
2. Click **Add Trigger** and select **Device**
3. Select your Sinapsi Alfa device
4. Choose from the available triggers (e.g., "Device unreachable")

### Device Trigger Automation Example

Get notified when your Sinapsi Alfa device goes offline and comes back online:

```yaml
automation:
  - alias: "Sinapsi Alfa Device Offline Alert"
    trigger:
      - platform: device
        domain: sinapsi_alfa
        device_id: YOUR_DEVICE_ID
        type: device_unreachable
    action:
      - service: notify.mobile_app
        data:
          title: "Sinapsi Alfa Offline"
          message: "The Sinapsi Alfa device is unreachable. Check network connection."

  - alias: "Sinapsi Alfa Device Recovered"
    trigger:
      - platform: device
        domain: sinapsi_alfa
        device_id: YOUR_DEVICE_ID
        type: device_recovered
    action:
      - service: notify.mobile_app
        data:
          title: "Sinapsi Alfa Online"
          message: "The Sinapsi Alfa device is back online and responding."
```

## Recovery Script

You can configure a Home Assistant script to run automatically when connection
failures reach the configured threshold. This is useful for automated recovery
actions like restarting a smart plug that powers the device.

### Configuration

1. Go to **Settings > Devices & Services > Alfa by Sinapsi**
2. Click **Configure** to open the options dialog
3. Select a script from the **Recovery script** dropdown
4. The script will run when the failure threshold is reached

### Script Variables

When the recovery script is executed, it receives these variables:

| Variable | Description |
|----------|-------------|
| `device_name` | Device name as configured in the integration |
| `host` | IP address or hostname of the device |
| `port` | TCP port (usually 502) |
| `serial_number` | Device serial number |
| `mac_address` | Device MAC address |
| `failures_count` | Number of consecutive failures |

### Example Recovery Script

Create a script that restarts a smart plug and sends a notification:

```yaml
script:
  alfa_recovery:
    alias: "Alfa Recovery Script"
    sequence:
      - service: notify.mobile_app
        data:
          title: "Alfa Recovery"
          message: >
            Device {{ device_name }} at {{ host }}:{{ port }} failed
            {{ failures_count }} times. Restarting power...
      - service: switch.turn_off
        target:
          entity_id: switch.alfa_smart_plug
      - delay:
          seconds: 10
      - service: switch.turn_on
        target:
          entity_id: switch.alfa_smart_plug
```

## Recovery Notifications

When the device recovers from a failure, the integration creates a persistent
repair notification with detailed timing information:

- **Failure started**: When the issue began
- **Script executed**: When the recovery script ran (if configured)
- **Recovery time**: When the device became responsive again
- **Total downtime**: Duration of the outage (e.g., "5m 23s")

These notifications appear in **Settings > System > Repairs** and require
user acknowledgment to dismiss.

## Use Cases

The Sinapsi Alfa integration enables several energy monitoring use cases:

### Real-time Energy Dashboard

Monitor your home's energy flow in real-time using the power sensors:

- **Power Imported** (`potenza_prelevata`): Current power consumption from grid
- **Power Exported** (`potenza_immessa`): Current power exported to grid (solar)
- **Power Produced** (`potenza_prodotta`): Current solar production
- **Power Consumed** (`potenza_consumata`): Total household consumption
- **Power Self-Consumed** (`potenza_auto_consumata`): Solar power used directly

### Energy Tracking for Billing

Track energy consumption by Italian time bands (F1-F6) for accurate billing:

- F1: Peak hours (Mon-Fri 8:00-19:00)
- F2: Mid-peak hours
- F3: Off-peak hours (nights, weekends, holidays)

Enable the daily time band sensors in the entity settings to track
consumption per band.

### Home Assistant Energy Dashboard

Add the integration's sensors to the HA Energy Dashboard for long-term tracking:

1. Go to **Settings** > **Dashboards** > **Energy**
1. Add `Energia Importata` as **Grid consumption**
1. Add `Energia Esportata` as **Return to grid**
1. Add `Energia Prodotta` as **Solar production**

## Automation Examples

### Notify When Solar Production Exceeds Consumption

```yaml
automation:
  - alias: "Solar Surplus Alert"
    trigger:
      - platform: template
        value_template: >
          {{ states('sensor.alfa_potenza_prodotta') | float(0) >
             states('sensor.alfa_potenza_consumata') | float(0) }}
        for:
          minutes: 5
    action:
      - service: notify.mobile_app
        data:
          title: "Solar Surplus"
          message: >
            Producing {{ states('sensor.alfa_potenza_prodotta') }} kW,
            consuming {{ states('sensor.alfa_potenza_consumata') }} kW.
            Good time to run high-power appliances!
```

### Track Daily Grid Import

```yaml
automation:
  - alias: "Daily Energy Report"
    trigger:
      - platform: time
        at: "23:55:00"
    action:
      - service: notify.mobile_app
        data:
          title: "Daily Energy Report"
          message: >
            Today's grid import: {{ states('sensor.alfa_energia_prelevata') }} kWh
            Solar production: {{ states('sensor.alfa_energia_prodotta') }} kWh
            Self-consumption: {{ states('sensor.alfa_energia_auto_consumata') }} kWh
```

### Start Appliances During Solar Production

```yaml
automation:
  - alias: "Start Dishwasher on Solar"
    trigger:
      - platform: numeric_state
        entity_id: sensor.alfa_potenza_prodotta
        above: 2.0  # kW
        for:
          minutes: 10
    condition:
      - condition: state
        entity_id: input_boolean.dishwasher_queued
        state: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.dishwasher
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.dishwasher_queued
```

## Known Limitations

- **One device per config entry**: Each config entry supports one Alfa
  device. To monitor multiple devices, add the integration multiple times
  with different host addresses
- **Italian market focus**: Sensor names and time bands (F1-F6) are specific
  to the Italian electricity market
- **Modbus TCP only**: The integration communicates via Modbus TCP; serial
  connections are not supported
- **No write operations**: The integration only reads data; it cannot
  control the device
- **MAC detection on VPN**: MAC address detection may fail over VPN
  connections. Enable "Skip MAC detection" during setup to use host-based
  device identification instead
- **Polling-based updates**: Data is fetched at the configured interval
  (30-600 seconds); real-time updates are not available

## Troubleshooting

### Enable Debug Logging

If you're experiencing issues, enable debug logging to help diagnose the
problem. Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sinapsi_alfa: debug
```

After adding this, restart Home Assistant for the changes to take effect.

### How to Get the FULL Debug Log

The standard **Settings > System > Logs** page only shows warnings and errors
by default. To get the complete debug log with all diagnostic information:

#### Method 1: Download Full Log File (Recommended)

1. Enable debug logging as shown above and restart Home Assistant
2. Reproduce the issue you're experiencing
3. Go to **Settings** > **System** > **Logs**
4. Click the three-dot menu (⋮) in the top-right corner
5. Select **Download full log**
6. This downloads the complete `home-assistant.log` file with ALL debug entries

#### Method 2: Access Log Files Directly

Log files are stored in your Home Assistant config directory:

- `config/home-assistant.log` - Current log file
- `config/home-assistant.log.1` - Previous log (rotated)

**Access methods by installation type:**

| Installation | How to Access |
|--------------|---------------|
| Home Assistant OS | Use the **File Editor** or **SSH & Web Terminal** add-on |
| Home Assistant Container | `docker exec -it homeassistant cat /config/home-assistant.log` |
| Home Assistant Core | Direct file access in your config directory |

#### Method 3: Filter Logs in Real-Time

For live debugging, use SSH or Terminal to watch logs in real-time:

```bash
# Filter for sinapsi_alfa entries only
tail -f /config/home-assistant.log | grep sinapsi_alfa

# Or view the last 500 lines
tail -n 500 /config/home-assistant.log | grep sinapsi_alfa
```

#### Important Notes

- The web UI logs page filters out debug-level messages by default
- Debug entries are only visible in the downloaded/raw log file
- After troubleshooting, consider removing the debug configuration to reduce
  log file size
- Log files rotate automatically; capture logs soon after reproducing an issue

### Reporting Issues

When [opening an issue][issues], please include:

1. **Diagnostic file**: Download from Settings > Devices & Services >
   Alfa by Sinapsi > three-dot menu (⋮) > Download diagnostics
1. **Home Assistant version** (Settings > About)
1. **Integration version** (Settings > Devices & Services > Alfa by Sinapsi)
1. **Debug logs** with timestamps showing the error
1. **Network setup** (local network, VPN, firewall, etc.)
1. **Steps to reproduce** the issue

The diagnostic file contains sanitized device information and configuration
that helps identify issues quickly. Sensitive data like IP addresses and
MAC addresses are automatically redacted.

## Development

This project uses a comprehensive test suite with 98% code coverage:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest tests/ --cov=custom_components/sinapsi_alfa --cov-report=term-missing -v

# Run linting
ruff format .
ruff check . --fix
```

**CI/CD Workflows:**

- **Tests**: Runs pytest with coverage on every push/PR to master
- **Lint**: Runs ruff format, ruff check, and ty type checker
- **Validate**: Runs hassfest and HACS validation
- **Release**: Automatically creates ZIP on GitHub release publish

## Coffee

_If you like this integration, I'll gladly accept some quality coffee,
but please don't feel obliged._ :)

[![BuyMeCoffee][buymecoffee-button]][buymecoffee]

______________________________________________________________________

[alfa]: https://www.alfabysinapsi.it/
[buymecoffee]: https://www.buymeacoffee.com/alexdelprete
[buymecoffee-button]: https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=%E2%98%95&slug=alexdelprete&button_colour=FFDD00&font_colour=000000&font_family=Lato&outline_colour=000000&coffee_colour=ffffff
[buymecoffee-shield]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-white?style=for-the-badge&logo=buymeacoffee&logoColor=white
[coverage]: https://codecov.io/github/alexdelprete/ha-sinapsi-alfa
[coverage-shield]: https://img.shields.io/codecov/c/github/alexdelprete/ha-sinapsi-alfa?style=for-the-badge
[downloads]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases
[downloads-shield]: https://img.shields.io/github/downloads/alexdelprete/ha-sinapsi-alfa/total?style=for-the-badge
[forum]: https://community.home-assistant.io/t/custom-integration-alfa-by-sinapsi-data-integration/705294
[forum-shield]: https://img.shields.io/badge/community-forum-darkred?style=for-the-badge
[hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[img-config]: https://raw.githubusercontent.com/alexdelprete/ha-sinapsi-alfa/master/gfxfiles/alfaconfig.png
[img-device]: https://raw.githubusercontent.com/alexdelprete/ha-sinapsi-alfa/master/gfxfiles/alfadevice.png
[img-sensors]: https://raw.githubusercontent.com/alexdelprete/ha-sinapsi-alfa/master/gfxfiles/alfasensors.gif
[issues]: https://github.com/alexdelprete/ha-sinapsi-alfa/issues
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=alexdelprete&repository=ha-sinapsi-alfa&category=integration
[releases]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases
[releases-shield]: https://img.shields.io/github/v/release/alexdelprete/ha-sinapsi-alfa?style=for-the-badge&color=darkgreen
[tests]: https://github.com/alexdelprete/ha-sinapsi-alfa/actions/workflows/test.yml
[tests-shield]: https://img.shields.io/github/actions/workflow/status/alexdelprete/ha-sinapsi-alfa/test.yml?style=for-the-badge&label=Tests
