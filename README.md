# HA Custom Component for 4-noks Elios4you energy monitoring device

[![GitHub Release][releases-shield]][releases]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Community Forum][forum-shield]][forum]

_This project is not endorsed by, directly affiliated with, maintained, authorized, or sponsored by 4-noks / Astrel Group_

# Introduction

HA Custom Component to integrate data from [Sinapsi Alfa](https://www.alfabysinapsi.it/) device.
Tested on my Alfa to monitor tha power/energy consumption and photovoltaic power/energy production directly from the provider's meter through the OpenMeter 2.0 protocol.

![alfa-device](https://github.com/alexdelprete/ha-sinapsi-alfa/assets/7027842/58b63c17-e532-4ffc-871f-95948193591e)

Alfa is a great product, it provides official measurements, and it provides local API to get the data (for now it's through ModBus).

So finally here we are with the first official version of the HA custom integration for Alfa devices. :)

### Features

- Installation/Configuration through Config Flow UI
- Sensor entities for all data provided by the device (I don't even know what some of the ones in the diagnostic category specifically represent)
- Switch entity to control the device internal relay
- Configuration options: Name, hostname, tcp port, polling period
- Reconfigure options (except device name) also at runtime: no restart needed.

# Installation through HACS

This integration is available in [HACS][hacs] official repository. Click this button to open HA directly on the integration page so you can easily install it:

[![Quick installation link](https://my.home-assistant.io/badges/hacs_repository.svg)][my-hacs]

1. Either click the button above, or navigate to HACS in Home Assistant and:
   - 'Explore & Download Repositories'
   - Search for '4-noks Elios4You'
   - Download
2. Restart Home Assistant
3. Go to Settings > Devices and Services > Add Integration
4. Search for and select '4-noks Elios4You' (if the integration is not found, do a hard-refresh (ctrl+F5) in the browser)
5. Proceed with the configuration

# Manual Installation

Download the source code archive from the release page. Unpack the archive and copy the contents of custom_components folder to your home-assistant config/custom_components folder. Restart Home Assistant, and then the integration can be added and configured through the native integration setup UI. If you don't see it in the native integrations list, press ctrl-F5 to refresh the browser while you're on that page and retry.

# Configuration

Configuration is done via config flow right after adding the integration. After the first configuration you can change parameters (except device name) at runtime through the integration page configuration, without the need to restart HA. 

- **custom name**: custom name for the device, that will be used as prefix for sensors created by the component
- **ip/hostname**: IP/hostname of the inverter - this is used as unique_id, if you change it and reinstall you will lose historical data, that's why I advice to use hostname, so you can change IP without losing historical data
- **tcp port**: TCP port of the device. tcp/5001 is the only known working port, but I preferred to leave it configurable
- **polling period**: frequency, in seconds, to read the registers and update the sensors

<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 50%;box-sizing: border-box;" src="https://github.com/alexdelprete/ha-sinapsi-alfa/assets/7027842/4a0b3168-4f4a-489f-90ac-eaff6edab6e2" alt="Config">

# Sensor view
<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 75%;box-sizing: border-box;" src="https://github.com/alexdelprete/ha-sinapsi-alfa/assets/7027842/7664a9a6-a5ed-4b9e-ab52-d863e2c1e523" alt="Config">

# Coffee

_If you like this integration, I'll gladly accept some quality coffee, but please don't feel obliged._ :)

[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]

---

[buymecoffee]: https://www.buymeacoffee.com/alexdelprete
[buymecoffee-shield]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-white?style=for-the-badge
[hacs]: https://hacs.xyz
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=alexdelprete&repository=ha-sinapsi-alfa&category=integration
[forum-shield]: https://img.shields.io/badge/community-forum-darkred?style=for-the-badge
[forum]: https://community.home-assistant.io/t/custom-component-4-noks-elios4you-data-integration/692883?u=alexdelprete
[releases-shield]: https://img.shields.io/github/v/release/alexdelprete/ha-sinapsi-alfa?style=for-the-badge&color=darkgreen
[releases]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases
