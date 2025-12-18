# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Development version for next release.

## [1.1.1] - 2025-12-18

**Patch release** - Fixes VPN connection timeout and adds Skip MAC Detection option.

### 🐛 Bug Fixes

- **Fixed VPN connection timeout** - MAC retrieval now happens before Modbus connection, preventing connection death during long network operations (Fixes #180)
- **Reduced MAC retry attempts** - Changed from 10 to 5 for faster fallback on high-latency networks

### ✨ New Features

- **Skip MAC Detection option** - New configuration option for VPN users to bypass MAC address retrieval and eliminate startup delay

Thanks to Lorenzo Canale ([@lorenzocanalelc](https://github.com/lorenzocanalelc)) for the detailed debug logs that helped identify the root cause.

**Full Release Notes:** [docs/releases/v1.1.1.md](docs/releases/v1.1.1.md)

**Full Changelog:** [v1.1.0...v1.1.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.0...v1.1.1)

---

## [1.1.0] - 2025-12-17

**Minor release** - User-configurable connection timeout for VPN/high-latency networks.

### ✨ New Features

- **User-configurable timeout** - New `timeout` parameter (5-60 seconds) in config flow and options (Addresses #180)
- **Increased default timeout** - Changed from 3-5s to 10s for better compatibility with typical networks

### 📝 Documentation

- Added ModbusLink documentation hint to CLAUDE.md
- Updated configuration parameters documentation

Thanks to Lorenzo Canale ([@lorenzocanalelc](https://github.com/lorenzocanalelc)) for reporting the VPN connection issue.

**Full Release Notes:** [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)

**Full Changelog:** [v1.0.1...v1.1.0](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.0.1...v1.1.0)

---

## [1.0.1] - 2025-12-11

**Patch release** - Fixes inverted import/export sensor icons.

### 🐛 Bug Fixes

- **Fixed inverted import/export icons** - Swapped `transmission-tower-import` and `transmission-tower-export` icons to match grid perspective (Fixes #178)

Thanks to Marco Lusini ([@met67](https://github.com/met67)) for reporting.

**Full Release Notes:** [docs/releases/v1.0.1.md](docs/releases/v1.0.1.md)

**Full Changelog:** [v1.0.0...v1.0.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.0.0...v1.0.1)

---

## [1.0.0] - 2025-12-07

**Major release** - ModbusLink migration with 7x performance improvement.

### 🚀 Performance Improvements

- **7x faster data collection** - 3.8s → 0.5s per update cycle
- **75% fewer Modbus requests** - 5 batch reads instead of 20 individual reads
- **Batch register reads** - Groups consecutive registers for efficiency

### 🔄 Breaking Changes

- **ModbusLink Migration** - Replaced pymodbus with ModbusLink library
- **Removed deprecated files** - `pymodbus_constants.py` and `pymodbus_payload.py` deleted

### 🐛 Bug Fixes

- **Fixed IPv4/IPv6 connection timeout** - Forces IPv4 to avoid dual-stack issues
- **Fixed Transaction ID mismatch** - Sequential batch reads for protocol compliance

### ✨ Code Improvements

- **Modern async API** - Native asyncio with context manager support
- **Enhanced debug logging** - Sensor values logged during data collection
- **Layered error handling** - Retry transient errors, fail fast on protocol errors
- **Cleaner codebase** - Removed 663 lines of deprecated pymodbus code

### ⚠️ Requirements

- Home Assistant 2025.10.0 or newer
- Python 3.13.2 or newer

**Full Release Notes:** [docs/releases/v1.0.0.md](docs/releases/v1.0.0.md)

**Full Changelog:** [v0.5.0...v1.0.0](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.5.0...v1.0.0)

---

## [1.0.0-beta.4] - 2025-12-07

**Protocol fix** - Sequential batch reads to avoid Transaction ID mismatches.

### 🐛 Bug Fixes

- **Fixed Transaction ID mismatch** - Replaced parallel `asyncio.gather()` with sequential batch reads (Modbus TCP can't handle concurrent requests on single connection)

### ⚠️ Beta Notice

ModbusLink is in **Alpha status** (Development Status 3). This release requires extensive testing.

**Full Release Notes:** [docs/releases/v1.0.0-beta.4.md](docs/releases/v1.0.0-beta.4.md)

**Full Changelog:** [v1.0.0-beta.3...v1.0.0-beta.4](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.0.0-beta.3...v1.0.0-beta.4)

---

## [1.0.0-beta.3] - 2025-12-07

**Connection fix** - Force IPv4 to avoid dual-stack timeout issues.

### 🐛 Bug Fixes

- **Fixed connection timeout** - `check_port()` now forces IPv4 (`socket.AF_INET`) to avoid timeouts when device only supports IPv4 but DNS returns IPv6 first

### ⚠️ Beta Notice

ModbusLink is in **Alpha status** (Development Status 3). This release requires extensive testing.

**Full Release Notes:** [docs/releases/v1.0.0-beta.3.md](docs/releases/v1.0.0-beta.3.md)

**Full Changelog:** [v1.0.0-beta.2...v1.0.0-beta.3](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.0.0-beta.2...v1.0.0-beta.3)

---

## [1.0.0-beta.2] - 2025-12-07

**Performance optimization** - ModbusLink best practices implementation.

### 🚀 Performance Improvements

- **Batch register reads** - 5 batches instead of 20 individual reads (~75% reduction)
- **Parallel batch reads** - Uses `asyncio.gather()` for concurrent execution (~4x faster)
- **Removed unnecessary lock** - `self._lock` removed since coordinator already serializes

### ✨ Code Improvements

- **Context manager usage** - `async with self._client:` for automatic connection handling
- **Layered error handling** - Retry transient errors, fail fast on protocol errors
- **Dynamic sensor mapping** - `SENSOR_MAP` built from `SENSOR_ENTITIES` + `REGISTER_BATCHES`

### 🧹 Code Quality

- Fixed ruff linting issues across all source files
- Fixed Pylance type errors with proper `BaseException` handling

### ⚠️ Beta Notice

ModbusLink is in **Alpha status** (Development Status 3). This release requires extensive testing.

**Full Release Notes:** [docs/releases/v1.0.0-beta.2.md](docs/releases/v1.0.0-beta.2.md)

**Full Changelog:** [v1.0.0-beta.1...v1.0.0-beta.2](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.0.0-beta.1...v1.0.0-beta.2)

---

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

**Full Changelog:** [v0.5.0...v1.0.0-beta.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.5.0...v1.0.0-beta.1)

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

**Full Changelog:** [v0.4.2...v0.5.0](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.4.2...v0.5.0)

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

**Full Changelog:** [v0.4.2...v0.5.0-beta.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.4.2...v0.5.0-beta.1)

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

**Full Changelog:** [v0.4.1...v0.4.2](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.4.1...v0.4.2)

---

[1.1.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.1
[1.1.0]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.0
[1.0.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.1
[1.0.0]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0
[1.0.0-beta.4]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.4
[1.0.0-beta.3]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.3
[1.0.0-beta.2]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.2
[1.0.0-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.1
[0.5.0]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.5.0
[0.5.0-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.5.0-beta.1
[0.4.2]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.4.2
