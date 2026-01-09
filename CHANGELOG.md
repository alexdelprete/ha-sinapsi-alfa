# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.6] - 2026-01-09

**Patch release** - Fixes empty recovery script validation error in options flow.

### 🐛 Bug Fixes

- **Fixed empty recovery script validation** - When saving options with an empty recovery script field, the form
  no longer shows "Entity is neither a valid entity ID nor a valid UUID" error
  (Fixes [#190](https://github.com/alexdelprete/ha-sinapsi-alfa/issues/190))

**Full Release Notes:** [docs/releases/v1.2.6.md](docs/releases/v1.2.6.md)

**Full Changelog:** [v1.2.5...v1.2.6](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.2.5...v1.2.6)

## [1.2.5] - 2026-01-08

**Patch release** - Lower minimum polling interval for faster sensor updates.

### ✨ Improvements

- **Lower minimum polling interval** - Reduced from 30s to 10s for more responsive sensor updates (Addresses [#74](https://github.com/alexdelprete/ha-sinapsi-alfa/issues/74))

Thanks to [@sigitm](https://github.com/sigitm) for the feature request!

**Full Release Notes:** [docs/releases/v1.2.5.md](docs/releases/v1.2.5.md)

**Full Changelog:** [v1.2.4...v1.2.5](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.2.4...v1.2.5)

## [1.2.4] - 2026-01-04

**Patch release** - Recovery notifications and test infrastructure improvements.

### 🐛 Bug Fixes

- **Fixed recovery notification display** - Switched from HA repair issues to `persistent_notification` for
  recovery notifications. When clicking the notification, the full message with timestamps now displays correctly.
- **Fixed duplicate notifications** - Recovery notifications no longer appear twice after acknowledging.

### 🧪 Testing Improvements

- **Improved test coverage** - Increased from 87% to 95%+ with comprehensive test suite
- **Fixed test infrastructure** - Enabled full Home Assistant integration tests in CI

**Full Release Notes:** [docs/releases/v1.2.4.md](docs/releases/v1.2.4.md)

**Full Changelog:** [v1.2.3...v1.2.4](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.2.3...v1.2.4)

## [1.2.3] - 2026-01-02

**Patch release** - Documentation improvements for development workflow.

### 📝 Documentation

- **Testing directives** - Added critical directive: never modify production code to make tests pass
- **Pre-commit mandatory** - Pre-commit checks now required before ANY commit (not just push)
- **CI testing recommendation** - Recommend running tests via CI only for consistent environment
- **Release Readiness Checklist** - Added mandatory checklist verification before tag/release
- **Download badge requirement** - All release notes must include download badge at top

**Full Release Notes:** [docs/releases/v1.2.3.md](docs/releases/v1.2.3.md)

**Full Changelog:** [v1.2.2...v1.2.3](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.2.2...v1.2.3)

## [1.2.2] - 2026-01-02

**Patch release** - Code quality improvements and hassfest validation fix.

### 🧹 Code Quality

- **Pre-commit hooks** - Added comprehensive pre-commit configuration (ruff, jsonlint, yamllint, pymarkdown)

### 🐛 Bug Fixes

- **Fixed hassfest validation** - Removed invalid `fix_flow` sections from translation files (issues using `ConfirmRepairFlow` don't need custom translations)

**Full Release Notes:** [docs/releases/v1.2.2.md](docs/releases/v1.2.2.md)

**Full Changelog:** [v1.2.1...v1.2.2](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.2.1...v1.2.2)

## [1.2.1] - 2026-01-02

**Stable release** - Feature alignment with ha-4noks-elios4you v1.1.0.

### ✨ New Features

- **Device triggers** - Home Assistant device automation triggers for connectivity events:
  - `device_unreachable` - Network/connection issues
  - `device_not_responding` - Modbus communication errors
  - `device_recovered` - Device back online
- **Configurable repair notifications** - New options in integration settings:
  - Toggle to enable/disable repair notifications
  - Configurable failure threshold (1-10)
  - Optional recovery script execution
- **Recovery script support** - Execute a script when failure threshold is reached
- **Recovery notifications** - Informative notification when device recovers with downtime details
- **Enhanced Options Flow UI** - Modern selectors (EntitySelector, NumberSelector)

### 🔧 Improvements

- **Config Entry VERSION 3** - Automatic migration from v2 with new options
- **Downtime tracking** - Track failure start time for accurate downtime reporting

**Full Release Notes:** [docs/releases/v1.2.1.md](docs/releases/v1.2.1.md)

**Full Changelog:** [v1.2.0...v1.2.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.2.0...v1.2.1)

## [1.2.0] - 2025-12-29

**Stable release** - Gold tier Quality Scale compliance with enterprise-grade features.

### ✨ New Features

- **Diagnostics support** - Download debug info from integration menu
- **Repair issues** - Automatic repair issue after 3 consecutive connection failures
- **Icon translations** - Custom icons for all 24 sensors via icons.json
- **Entity translations** - 10 languages (de, en, es, et, fi, fr, it, nb, pt, sv)
- **Exception translations** - Error messages in user's language
- **Entity disabled by default** - F1-F6 time band sensors disabled by default
- **Improved terminology** - Changed from Drawn/Fed to Imported/Exported

### 🔧 Improvements

- **Full type annotations** - mypy strict typing compliance
- **Comprehensive test suite** - 95% coverage threshold
- **pyproject.toml consolidation** - Modern Python packaging
- **GitHub Actions CI** - Automated testing workflow

**Full Release Notes:** [docs/releases/v1.2.0.md](docs/releases/v1.2.0.md)

**Full Changelog:** [v1.1.11...v1.2.0](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.11...v1.2.0)

## [1.1.12-beta.1] - 2025-12-29

**Beta release** - Gold tier Quality Scale implementation. Testing required.

### ✨ New Features

- **Diagnostics support** - Download debug info from integration menu
- **Repair issues** - Automatic repair issue after 3 consecutive connection failures
- **Icon translations** - Custom icons for all 24 sensors via icons.json
- **Entity translations** - 10 languages (de, en, es, et, fi, fr, it, nb, pt, sv)
- **Exception translations** - Error messages in user's language
- **Entity disabled by default** - F1-F6 time band sensors disabled by default

### 🔧 Improvements

- **Full type annotations** - mypy strict typing compliance
- **95% test coverage** - Increased from 85%
- **README restructured** - Proper markdown formatting

**Full Release Notes:** [docs/releases/v1.1.12-beta.1.md](docs/releases/v1.1.12-beta.1.md)

**Full Changelog:** [v1.1.11...v1.1.12-beta.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.11...v1.1.12-beta.1)

## [1.1.11] - 2025-12-27

**Stable release** - Config entry migration and options flow improvements.

### ⚠️ Breaking Changes

- **Config Entry v2** - Migration from v1 to v2 (automatic)

### ✨ Improvements

- **OptionsFlowWithReload** - Options changes now auto-reload integration
- **Better type hints** - Improved code quality in config flow
- **Cleaner code** - Removed legacy migration code, improved method naming

### 🐛 Bug Fixes

- **Options Flow** - Fixed initialization error

**Full Release Notes:** [docs/releases/v1.1.11.md](docs/releases/v1.1.11.md)

**Full Changelog:** [v1.1.10...v1.1.11](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.10...v1.1.11)

## [1.1.11-beta.2] - 2025-12-27

**Beta release** - Fixes options flow error from beta.1.

### 🐛 Bug Fixes

- **Options Flow** - Fixed "500 Internal Server Error" when opening options

**Full Release Notes:** [docs/releases/v1.1.11-beta.2.md](docs/releases/v1.1.11-beta.2.md)

**Full Changelog:** [v1.1.11-beta.1...v1.1.11-beta.2](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.11-beta.1...v1.1.11-beta.2)

## [1.1.11-beta.1] - 2025-12-27

**Beta release** - Config entry migration and options flow improvements. Testing required.

### ⚠️ Breaking Changes

- **Config Entry v2** - Migration from v1 to v2 (automatic, but please verify)

### ✨ Improvements

- **OptionsFlowWithReload** - Options changes now auto-reload integration
- **Better type hints** - Improved code quality in config flow
- **Cleaner code** - Removed legacy migration code, improved method naming

**Full Release Notes:** [docs/releases/v1.1.11-beta.1.md](docs/releases/v1.1.11-beta.1.md)

**Full Changelog:** [v1.1.10...v1.1.11-beta.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.10...v1.1.11-beta.1)

## [1.1.10] - 2025-12-25

**Patch release** - Updates ModbusLink to 1.3.2 for English-only error messages.

### ✨ Improvements

- **English-only errors** - Exception messages are now fully in English (ModbusLink 1.3.2)
- **Updated ModbusLink dependency** - Bumped from `>=1.3.1` to `>=1.3.2`

**Full Release Notes:** [docs/releases/v1.1.10.md](docs/releases/v1.1.10.md)

**Full Changelog:** [v1.1.9...v1.1.10](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.9...v1.1.10)

## [1.1.9] - 2025-12-24

**Patch release** - Improves protocol error recovery to reduce recovery time.

### 🐛 Bug Fixes

- **Faster protocol error recovery** - Increased reset delay from 0.5s to 1.0s to better clear TCP buffers
- **Early abort on cascade errors** - If 3+ protocol errors occur in a single update cycle, abort early instead of
  retrying all batches (reduces worst-case recovery from ~3 minutes to under 1 minute)

**Full Release Notes:** [docs/releases/v1.1.9.md](docs/releases/v1.1.9.md)

**Full Changelog:** [v1.1.8...v1.1.9](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.8...v1.1.9)

## [1.1.8] - 2025-12-21

**Patch release** - Fixes integration reload and improves protocol error recovery.

### 🐛 Bug Fixes

- **Fixed integration reload** - Added missing `close()` method to API class, allowing integration to reload without requiring Home Assistant restart
- **Improved protocol error recovery** - Transaction ID mismatch and CRC errors now trigger connection reset and retry instead of immediate failure
- **Added connection reset method** - New `_reset_connection()` clears stale responses by closing and reopening the transport

**Full Release Notes:** [docs/releases/v1.1.8.md](docs/releases/v1.1.8.md)

**Full Changelog:** [v1.1.7...v1.1.8](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.7...v1.1.8)

______________________________________________________________________

## [1.1.7] - 2025-12-19

**Patch release** - Fixes ModbusLink import path for Language and ModbusLogger.

### 🐛 Bug Fixes

- **Fixed ModbusLink import path** - Import `Language` and `ModbusLogger` from `modbuslink.utils.logging` (not exported from main package)

**Full Release Notes:** [docs/releases/v1.1.7.md](docs/releases/v1.1.7.md)

**Full Changelog:** [v1.1.6...v1.1.7](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.6...v1.1.7)

______________________________________________________________________

## [1.1.6] - 2025-12-19

**Patch release** - Fixes critical ModbusLink version requirement bug.

### 🐛 Bug Fixes

- **Fixed ModbusLink requirement** - Changed from `>=1.3.2` (doesn't exist) to `>=1.3.1` (correct version with language support)

**Full Release Notes:** [docs/releases/v1.1.6.md](docs/releases/v1.1.6.md)

**Full Changelog:** [v1.1.5...v1.1.6](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.5...v1.1.6)

______________________________________________________________________

## [1.1.5] - 2025-12-18

**Minor release** - Updates ModbusLink to v1.3.1 with English logging support.

### ✨ Improvements

- **English-only logging** - Configure ModbusLink to use English logging (fixes mixed Chinese/English log messages)
- **Updated ModbusLink dependency** - Bumped from `>=1.2.0` to `>=1.3.1`

Thanks to the ModbusLink developer ([@Miraitowa-la](https://github.com/Miraitowa-la)) for the quick fix!

**Full Release Notes:** [docs/releases/v1.1.5.md](docs/releases/v1.1.5.md)

**Full Changelog:** [v1.1.4...v1.1.5](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.4...v1.1.5)

______________________________________________________________________

## [1.1.4] - 2025-12-18

**Patch release** - Changes Connection Timeout from slider to number input field.

### 🐛 Bug Fixes

- **Changed Connection Timeout to number input** - Replaced slider with text input field for better UX (matches Polling Period style)
- **Added timeout bounds enforcement** - Coordinator now enforces 5-60s range like scan_interval

**Full Release Notes:** [docs/releases/v1.1.4.md](docs/releases/v1.1.4.md)

**Full Changelog:** [v1.1.3...v1.1.4](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.3...v1.1.4)

______________________________________________________________________

## [1.1.3] - 2025-12-18

**Patch release** - Fixes Connection Timeout slider description display issue.

### 🐛 Bug Fixes

- **Fixed Connection Timeout description display** - Removed `data_description` for slider fields (doesn't render properly in HA UI), moved range info back to field label

**Full Release Notes:** [docs/releases/v1.1.3.md](docs/releases/v1.1.3.md)

**Full Changelog:** [v1.1.2...v1.1.3](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.2...v1.1.3)

______________________________________________________________________

## [1.1.2] - 2025-12-18

**Patch release** - Fixes UI translation issues in configuration flow.

### 🐛 Bug Fixes

- **Fixed missing translation for Skip MAC Detection** - Checkbox now shows proper label instead of variable name
- **Improved Connection Timeout field** - Shortened label with detailed description below for better spacing

### 📝 Documentation

- Added `data_description` sections to translation files for enhanced field descriptions
- Updated Portuguese translations for new fields

**Full Release Notes:** [docs/releases/v1.1.2.md](docs/releases/v1.1.2.md)

**Full Changelog:** [v1.1.1...v1.1.2](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.1.1...v1.1.2)

______________________________________________________________________

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

______________________________________________________________________

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

______________________________________________________________________

## [1.0.1] - 2025-12-11

**Patch release** - Fixes inverted import/export sensor icons.

### 🐛 Bug Fixes

- **Fixed inverted import/export icons** - Swapped `transmission-tower-import` and `transmission-tower-export` icons to match grid perspective (Fixes #178)

Thanks to Marco Lusini ([@met67](https://github.com/met67)) for reporting.

**Full Release Notes:** [docs/releases/v1.0.1.md](docs/releases/v1.0.1.md)

**Full Changelog:** [v1.0.0...v1.0.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.0.0...v1.0.1)

______________________________________________________________________

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

______________________________________________________________________

## [1.0.0-beta.4] - 2025-12-07

**Protocol fix** - Sequential batch reads to avoid Transaction ID mismatches.

### 🐛 Bug Fixes

- **Fixed Transaction ID mismatch** - Replaced parallel `asyncio.gather()` with sequential batch reads (Modbus TCP can't handle concurrent requests on single connection)

### ⚠️ Beta Notice

ModbusLink is in **Alpha status** (Development Status 3). This release requires extensive testing.

**Full Release Notes:** [docs/releases/v1.0.0-beta.4.md](docs/releases/v1.0.0-beta.4.md)

**Full Changelog:** [v1.0.0-beta.3...v1.0.0-beta.4](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.0.0-beta.3...v1.0.0-beta.4)

______________________________________________________________________

## [1.0.0-beta.3] - 2025-12-07

**Connection fix** - Force IPv4 to avoid dual-stack timeout issues.

### 🐛 Bug Fixes

- **Fixed connection timeout** - `check_port()` now forces IPv4 (`socket.AF_INET`) to avoid timeouts when device only supports IPv4 but DNS returns IPv6 first

### ⚠️ Beta Notice

ModbusLink is in **Alpha status** (Development Status 3). This release requires extensive testing.

**Full Release Notes:** [docs/releases/v1.0.0-beta.3.md](docs/releases/v1.0.0-beta.3.md)

**Full Changelog:** [v1.0.0-beta.2...v1.0.0-beta.3](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v1.0.0-beta.2...v1.0.0-beta.3)

______________________________________________________________________

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

______________________________________________________________________

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

______________________________________________________________________

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

______________________________________________________________________

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

- helpers.py, const.py, api.py, `__init__.py`, sensor.py, coordinator.py, config_flow.py, manifest.json

### ✅ Preserved Features

All Sinapsi-specific features remain unchanged: Modbus addresses, Italian sensor names, special value handling, calculated sensors.

**Full Release Notes:** [docs/releases/v0.5.0-beta.1.md](docs/releases/v0.5.0-beta.1.md)

**Full Changelog:** [v0.4.2...v0.5.0-beta.1](https://github.com/alexdelprete/ha-sinapsi-alfa/compare/v0.4.2...v0.5.0-beta.1)

______________________________________________________________________

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

______________________________________________________________________

[0.4.2]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.4.2
[0.5.0]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.5.0
[0.5.0-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v0.5.0-beta.1
[1.0.0]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0
[1.0.0-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.1
[1.0.0-beta.2]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.2
[1.0.0-beta.3]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.3
[1.0.0-beta.4]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.0-beta.4
[1.0.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.0.1
[1.1.0]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.0
[1.1.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.1
[1.1.10]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.10
[1.1.11]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.11
[1.1.11-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.11-beta.1
[1.1.11-beta.2]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.11-beta.2
[1.1.12-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.12-beta.1
[1.1.2]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.2
[1.1.3]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.3
[1.1.4]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.4
[1.1.5]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.5
[1.1.6]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.6
[1.1.7]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.7
[1.1.8]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.8
[1.1.9]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.1.9
[1.2.0]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.2.0
[1.2.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.2.1
[1.2.2]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.2.2
[1.2.3]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.2.3
[1.2.4]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.2.4
[1.2.6]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.2.6
[1.2.5]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.2.5
[1.2.4-beta.1]: https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/v1.2.4-beta.1
