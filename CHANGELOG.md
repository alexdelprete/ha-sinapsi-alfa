# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

No unreleased changes at this time.

## [1.0.0-beta.1] - 2025-12-06

**Major architectural change** - Migration from pymodbus to ModbusLink library.

### 🔄 Breaking Changes

- **Modbus Library Migration** - Switched from `pymodbus>=3.11.2` to `modbuslink>=1.2.0`
- **Removed deprecated files** - `pymodbus_constants.py` and `pymodbus_payload.py` deleted

### ✨ Improvements

- **Modern async API** - Native asyncio with `AsyncModbusClient` and `AsyncTcpTransport`
- **Cleaner codebase** - Removed 663 lines of deprecated pymodbus payload decoder code
- **Simplified register decoding** - Direct `List[int]` return from read operations
- **Better exception handling** - Structured `ModbusConnectionError`, `ModbusTimeoutError`, `ModbusException`

### ⚠️ Beta Notice

ModbusLink is in **Alpha status** (Development Status 3). This release requires extensive testing.

**Full Release Notes:** [docs/releases/v1.0.0-beta.1.md](docs/releases/v1.0.0-beta.1.md)

**Full Changelog:** https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.5.0...v1.0.0-beta.1

---

## [0.5.0] - 2025-10-15

Official stable release with Python 3.13 support, Home Assistant 2025.10 compatibility, comprehensive code quality improvements, and critical bug fixes.

### 🚀 Platform Compatibility

- **Python 3.13 Support** - Required for Home Assistant 2025.10.2+ (which requires Python >= 3.13.2)
- **Home Assistant 2025.10 Compatibility** - Updated minimum HA requirement to 2025.10.0
- **Updated Dependencies** - pymodbus 3.11.2, homeassistant 2025.10.2, HACS minimum 2025.10.0

### 🐛 Critical Bug Fixes

- **Fixed Sensor Availability** - Sensors now properly show as "unavailable" when device is offline
- **Fixed Resource Leak** - Integration unload now properly cleans up resources
- **Fixed Connection Health Tracking** - Better error recovery and diagnostics

### ✨ Code Quality Improvements

- Created centralized logging helpers with consistent context-based format
- Added custom exception classes: `SinapsiConnectionError`, `SinapsiModbusError`
- Improved validation with constants and better config flow UX
- Code modernization with `@callback` decorators and proper cleanup patterns

### 📦 Dependencies & CI/CD

- Updated ruff from 0.13.1 to 0.14.0 with Python 3.13 target
- Updated GitHub Actions: softprops/action-gh-release 2.3.3 → 2.4.1
- Updated stefanzweifel/git-auto-commit-action 6.0.1 → 7.0.0
- Python version in CI upgraded from 3.11 to 3.13

### ⚠️ Breaking Changes

- **Requires Home Assistant 2025.10.0 or newer**
- **Requires Python 3.13.2 or newer** (managed by Home Assistant)

**Full Release Notes:** [docs/releases/v0.5.0.md](docs/releases/v0.5.0.md)

**Full Changelog:** https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.4.2...v0.5.0

---

## [0.5.0-beta.1] - 2025-10-12

⚠️ **This is a BETA release** - Please test thoroughly before using in production

Beta release aligning ha-sinapsi-alfa with critical fixes and improvements from ha-abb-powerone-pvi-sunspec v4.1.5.

### 🐛 Critical Bug Fixes

- **Fixed Sensor Availability** - Sensors now properly show as "unavailable" when device is offline
- **Fixed Resource Leak** - Integration unload now only cleans up resources when platform unload succeeds
- **Added Connection Health Tracking** - Better error recovery and diagnostics

### ✨ Code Quality Improvements

- Standardized logging with centralized helpers
- Enhanced error handling with custom exception classes
- Improved validation (MAX_SCAN_INTERVAL, port validation, vol.Clamp)
- Code modernization with @callback decorators

### 📦 Files Modified

- helpers.py, const.py, api.py, __init__.py, sensor.py, coordinator.py, config_flow.py, manifest.json

### ✅ Preserved Features

All Sinapsi-specific features remain unchanged: Modbus addresses, Italian sensor names, special value handling, calculated sensors.

**Full Release Notes:** [docs/releases/v0.5.0-beta.1.md](docs/releases/v0.5.0-beta.1.md)

**Full Changelog:** https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.4.2...v0.5.0-beta.1

---

## [0.4.2] - 2025-09-22

Stable release with pymodbus 3.11.1 compatibility and improved MAC address detection.

### 🚀 Features & Improvements

- **Updated pymodbus to 3.11.1** - Ensures compatibility with Home Assistant 2025.9.x and later
- **Improved network MAC address detection** - Enhanced getmac functionality for better device identification

### 🧹 Code Quality

- Applied style fixes using ruff linter
- Removed Claude settings from version control

### 📦 Dependencies

- pymodbus: Updated to 3.11.1
- ruff: Updated to 0.13.1
- actions/setup-python: 5.6.0 → 6.0.0
- actions/checkout: 4.2.2 → 5.0.0
- softprops/action-gh-release: 2.3.2 → 2.3.3

### ⚠️ Requirements

- **Minimum Home Assistant version: 2025.9.0**

**Full Release Notes:** [docs/releases/v0.4.2.md](docs/releases/v0.4.2.md)

**Full Changelog:** https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.4.1...v0.4.2

---

[1.0.0-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.1
[0.5.0]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.5.0
[0.5.0-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.5.0-beta.1
[0.4.2]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.4.2
