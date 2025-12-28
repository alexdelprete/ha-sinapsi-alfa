# HA Custom Integration: Alfa by Sinapsi energy monitoring device

[![GitHub Release][releases-shield]][releases]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Community Forum][forum-shield]][forum]

[![GitHub Activity][commits-shield]][commits]
![Project Maintenance][maintenance-shield]
[![hacs][hacs-shield]][hacs]

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
- **Options flow**: Adjust polling interval and connection timeout at runtime
- **Reconfigure flow**: Change device name, host, port, and skip MAC detection
- All changes apply immediately without Home Assistant restart

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
1. Adjust **Polling interval** and **Connection timeout**
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

## Use Cases

The Sinapsi Alfa integration enables several energy monitoring use cases:

### Real-time Energy Dashboard

Monitor your home's energy flow in real-time using the power sensors:

- **Power Drawn** (`potenza_prelevata`): Current power consumption from grid
- **Power Fed** (`potenza_immessa`): Current power exported to grid (solar)
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
1. Add `Energia Prelevata` as **Grid consumption**
1. Add `Energia Immessa` as **Return to grid**
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

- **Single device per integration**: Each config entry supports one Alfa
  device. To monitor multiple devices, add the integration multiple times
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

### View and Download Logs

1. Go to **Settings** > **System** > **Logs**
1. Click **Load Full Logs** to see all log entries
1. Use the search box to filter for `sinapsi_alfa`
1. Click **Download Full Log** to save the complete log file

Alternatively, you can access logs directly from the file system at:

- `config/home-assistant.log` (current log)
- `config/home-assistant.log.1` (previous log)

### Reporting Issues

When [opening an issue][issues], please include:

1. **Home Assistant version** (Settings > About)
1. **Integration version** (Settings > Devices & Services > Alfa by Sinapsi)
1. **Debug logs** with timestamps showing the error
1. **Network setup** (local network, VPN, firewall, etc.)
1. **Steps to reproduce** the issue

## Coffee

_If you like this integration, I'll gladly accept some quality coffee,
but please don't feel obliged._ :)

[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]

______________________________________________________________________

[alfa]: https://www.alfabysinapsi.it/
[buymecoffee]: https://www.buymeacoffee.com/alexdelprete
[buymecoffee-shield]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-white?style=for-the-badge
[commits]: https://github.com/alexdelprete/ha-sinapsi-alfa/commits/master
[commits-shield]: https://img.shields.io/github/commit-activity/y/alexdelprete/ha-sinapsi-alfa.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/t/custom-integration-alfa-by-sinapsi-data-integration/705294
[forum-shield]: https://img.shields.io/badge/community-forum-darkred?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-shield]: https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge
[img-config]: https://raw.githubusercontent.com/alexdelprete/ha-sinapsi-alfa/master/gfxfiles/alfaconfig.png
[img-device]: https://raw.githubusercontent.com/alexdelprete/ha-sinapsi-alfa/master/gfxfiles/alfadevice.png
[img-sensors]: https://raw.githubusercontent.com/alexdelprete/ha-sinapsi-alfa/master/gfxfiles/alfasensors.gif
[issues]: https://github.com/alexdelprete/ha-sinapsi-alfa/issues
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40alexdelprete-blue.svg?style=for-the-badge
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=alexdelprete&repository=ha-sinapsi-alfa&category=integration
[releases]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases
[releases-shield]: https://img.shields.io/github/v/release/alexdelprete/ha-sinapsi-alfa?style=for-the-badge&color=darkgreen
