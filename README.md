# HA Custom Integration: Alfa by Sinapsi energy monitoring device

[![GitHub Release][releases-shield]][releases][![BuyMeCoffee][buymecoffee-shield]][buymecoffee][![Community Forum][forum-shield]][forum]

[![GitHub Activity][commits-shield]][commits]![Project Maintenance][maintenance-shield][![hacs][hacs-shield]][hacs]

_This project is not endorsed by, directly affiliated with, maintained, authorized, or sponsored by Sinapsi_

# Introduction

HA Custom Component to integrate data from [Sinapsi Alfa](https://www.alfabysinapsi.it/) device.
Tested on my Alfa to monitor the power/energy consumption and photovoltaic power/energy production directly from the energy provider's OpenMeter 2.0.

<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 40%;box-sizing: border-box;" src="https://github.com/alexdelprete/ha-sinapsi-alfa/blob/9cdc7bf681db4ad83700ddaf8d7e745a8769e684/gfxfiles/alfadevice.png" alt="Config">

Alfa is a great product, it provides official measurements, and it provides local API to get the data (for now it's through ModBus).

So finally here we are with the first official version of the HA custom integration for Alfa devices. :)

### Features

- Installation/Configuration through Config Flow UI
- Sensor entities for all data provided by the device
- **Options flow**: Adjust polling interval and connection timeout at runtime
- **Reconfigure flow**: Change device name, host, port, and skip MAC detection settings
- All changes apply immediately without Home Assistant restart

# Installation through HACS

This integration is available in [HACS][hacs] official repository. Click this button to open HA directly on the integration page so you can easily install it:

[![Quick installation link](https://my.home-assistant.io/badges/hacs_repository.svg)][my-hacs]

1. Either click the button above, or navigate to HACS in Home Assistant and:
   - 'Explore & Download Repositories'
   - Search for 'Alfa by Sinapsi'
   - Download
2. Restart Home Assistant
3. Go to Settings > Devices and Services > Add Integration
4. Search for and select 'Alfa by Sinapsi' (if the integration is not found, do a hard-refresh (ctrl+F5) in the browser)
5. Proceed with the configuration

# Manual Installation

Download the source code archive from the release page. Unpack the archive and copy the contents of custom_components folder to your home-assistant config/custom_components folder. Restart Home Assistant, and then the integration can be added and configured through the native integration setup UI. If you don't see it in the native integrations list, press ctrl-F5 to refresh the browser while you're on that page and retry.

# Configuration

Configuration is done via config flow right after adding the integration.

## Initial Setup

During initial setup, you configure all settings:

- **Device name**: Custom name for the device (used as prefix for sensor names)
- **IP/Hostname**: IP address or hostname of the Alfa device
- **TCP port**: Modbus TCP port (default: 502)
- **Polling interval**: How often to read data from the device (30-600 seconds)
- **Connection timeout**: How long to wait for device response (5-60 seconds)
- **Skip MAC detection**: Enable for VPN connections (uses host-based ID instead of MAC)

<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 50%;box-sizing: border-box;" src="https://github.com/alexdelprete/ha-sinapsi-alfa/blob/9cdc7bf681db4ad83700ddaf8d7e745a8769e684/gfxfiles/alfaconfig.png" alt="Config">

## Runtime Options

After installation, you can adjust runtime settings without restart:

1. Go to **Settings** > **Devices & Services** > **Alfa by Sinapsi**
2. Click **Configure** to open the options dialog
3. Adjust **Polling interval** and **Connection timeout**
4. Click **Submit** - changes apply immediately

## Reconfiguring Connection Settings

To change the device name, host, port, or skip MAC detection:

1. Go to **Settings** > **Devices & Services** > **Alfa by Sinapsi**
2. Click the **three-dot menu** (⋮) on the integration card
3. Select **Reconfigure**
4. Update the settings and click **Submit**

Note: Entity IDs are based on the device serial number, so changing the device name or host will not affect your historical data or automations using entity IDs.

# Sensor view

<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 75%;box-sizing: border-box;" src="https://github.com/alexdelprete/ha-sinapsi-alfa/blob/9cdc7bf681db4ad83700ddaf8d7e745a8769e684/gfxfiles/alfasensors.gif" alt="Config">

# Troubleshooting

## Enable Debug Logging

If you're experiencing issues, enable debug logging to help diagnose the problem. Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sinapsi_alfa: debug
```

After adding this, restart Home Assistant for the changes to take effect.

## View and Download Logs

1. Go to **Settings** > **System** > **Logs**
2. Click **Load Full Logs** to see all log entries
3. Use the search box to filter for `sinapsi_alfa`
4. Click **Download Full Log** to save the complete log file

Alternatively, you can access logs directly from the file system at:

- `config/home-assistant.log` (current log)
- `config/home-assistant.log.1` (previous log)

## Reporting Issues

When [opening an issue](https://github.com/alexdelprete/ha-sinapsi-alfa/issues), please include:

1. **Home Assistant version** (Settings > About)
2. **Integration version** (Settings > Devices & Services > Alfa by Sinapsi)
3. **Debug logs** with timestamps showing the error
4. **Network setup** (local network, VPN, firewall, etc.)
5. **Steps to reproduce** the issue

# Coffee

_If you like this integration, I'll gladly accept some quality coffee, but please don't feel obliged._ :)

[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]

---
[commits-shield]: https://img.shields.io/github/commit-activity/y/alexdelprete/ha-sinapsi-alfa.svg?style=for-the-badge
[commits]: https://github.com/alexdelprete/ha-sinapsi-alfa/commits/master
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40alexdelprete-blue.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/alexdelprete
[buymecoffee-shield]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-white?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-darkred?style=for-the-badge
[forum]: https://community.home-assistant.io/t/custom-integration-alfa-by-sinapsi-data-integration/705294
[hacs]: https://github.com/hacs/integration
[hacs-shield]: https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=alexdelprete&repository=ha-sinapsi-alfa&category=integration
[releases]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases
[releases-shield]: https://img.shields.io/github/v/release/alexdelprete/ha-sinapsi-alfa?style=for-the-badge&color=darkgreen
