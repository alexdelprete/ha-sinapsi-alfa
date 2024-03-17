# HA Custom Component: Alfa by Sinapsi energy monitoring device

[![GitHub Release][releases-shield]][releases][![BuyMeCoffee][buymecoffee-shield]][buymecoffee][![Community Forum][forum-shield]][forum]

[![GitHub Activity][commits-shield]][commits]![Project Maintenance][maintenance-shield][![hacs][hacs-shield]][hacs]

_This project is not endorsed by, directly affiliated with, maintained, authorized, or sponsored by Sinapsi_

# Introduction

HA Custom Component to integrate data from [Sinapsi Alfa](https://www.alfabysinapsi.it/) device.
Tested on my Alfa to monitor tha power/energy consumption and photovoltaic power/energy production directly from the energy provider's meter that support the OpenMeter 2.0 protocol.

![alfa-device](upload://am5ecsbONooZ4GZocipotzN2BP0.png)

Alfa is a great product, it provides official measurements, and it provides local API to get the data (for now it's through ModBus).

So finally here we are with the first official version of the HA custom integration for Alfa devices. :)

### Features

- Installation/Configuration through Config Flow UI
- Sensor entities for all data provided by the device
- Configuration options: Name, hostname, tcp port, polling period
- Reconfigure options (except device name) also at runtime: no restart needed.

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

Configuration is done via config flow right after adding the integration. After the first configuration you can change parameters (except device name) at runtime through the integration page configuration, without the need to restart HA. 

- **custom name**: custom name for the device, that will be used as prefix for sensors created by the component
- **ip/hostname**: IP/hostname of the inverter - this is used as unique_id, if you change it and reinstall you will lose historical data, that's why I advice to use hostname, so you can change IP without losing historical data
- **tcp port**: TCP port of the device. tcp/502 is the only known working port, but I preferred to leave it configurable
- **polling period**: frequency, in seconds, to read the registers and update the sensors

<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 50%;box-sizing: border-box;" src="upload://kL4ybstJKBvYVI3blIqs8raRP2m.png" alt="Config">

# Sensor view
<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 75%;box-sizing: border-box;" src="upload://a57bCqjn4gxGLXqDx1kvGtpTFap.gif" alt="Config">

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
[forum]: https://community.home-assistant.io/t/custom-component-4-noks-elios4you-data-integration/692883?u=alexdelprete
[hacs]: https://github.com/hacs/integration
[hacs-shield]: https://img.shields.io/badge/HACS-Default-darkgreen.svg?style=for-the-badge
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=alexdelprete&repository=ha-sinapsi-alfa&category=integration
[releases]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases
[releases-shield]: https://img.shields.io/github/v/release/alexdelprete/ha-sinapsi-alfa?style=for-the-badge
