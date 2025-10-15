# Claude Code Development Guidelines

## Project Overview

This is a Home Assistant custom integration for **Sinapsi Alfa** energy monitoring devices using Modbus TCP protocol. The Alfa device monitors power/energy consumption and photovoltaic production directly from the energy provider's OpenMeter 2.0.

This integration is based on and aligned with [ha-abb-powerone-pvi-sunspec](https://github.com/alexdelprete/ha-abb-powerone-pvi-sunspec), sharing similar architecture and code quality standards.

## Code Architecture

### Core Components

1. **`__init__.py`** - Integration lifecycle management
   - `async_setup_entry()` - Initialize coordinator and platforms
   - `async_unload_entry()` - Clean shutdown and resource cleanup
   - `async_migrate_entry()` - Config migration logic
   - Uses `runtime_data` for storing coordinator and update listener

2. **`api.py`** - Modbus TCP communication layer
   - `SinapsiAlfaAPI` class handles all Modbus operations
   - Reads device-specific registers (power, energy, time band data)
   - Implements connection pooling and timeout handling
   - Custom exception handling for device-specific error codes

3. **`coordinator.py`** - Data update coordination
   - `SinapsiAlfaCoordinator` manages polling cycles
   - Handles data refresh from API
   - Error handling and retry logic
   - Enforces MAX_SCAN_INTERVAL constraints

4. **`config_flow.py`** - UI configuration
   - ConfigFlow for initial setup
   - OptionsFlow for runtime reconfiguration
   - Validates host, port, scan_interval
   - Uses `vol.Clamp()` for better UX

5. **`sensor.py`** - Entity platform
   - Creates 24 sensor entities from coordinator data
   - Includes 4 calculated sensors (potenza_consumata, potenza_auto_consumata, energia_consumata, energia_auto_consumata)
   - Italian sensor names for local market
   - Proper availability tracking

## Sinapsi-Specific Features

### Device Constants
```python
MANUFACTURER = "Sinapsi"
MODEL = "Alfa"
DEFAULT_PORT = 502
DEFAULT_DEVICE_ID = 1
```

### Modbus Registers
The integration reads from specific Modbus addresses:
- Power readings: addresses 2, 9, 12, 19, 921
- Energy readings: addresses 5, 15, 924
- Daily energy by time band: F1-F6 (addresses 30-64)
- Time band info: address 203
- Event data: addresses 780, 782

### Special Value Handling
```python
INVALID_DISTACCO_VALUE = 65535  # Invalid disconnect timer value
MAX_EVENT_VALUE = 4294967294     # Maximum event timestamp value
```

### Calculated Sensors
The integration provides 4 calculated sensors derived from device readings:
- **Potenza Consumata**: Total power consumed (Prelevata + Prodotta - Immessa)
- **Potenza Auto Consumata**: Self-consumed PV power (Prodotta - Immessa)
- **Energia Consumata**: Total energy consumed (Prelevata + Prodotta - Immessa)
- **Energia Auto Consumata**: Self-consumed PV energy (Prodotta - Immessa)

### Italian Sensor Names
All sensors use Italian names for the local market:
- "Potenza Prelevata" (Power Drawn)
- "Potenza Immessa" (Power Fed)
- "Potenza Prodotta" (Power Produced)
- "Energia Prelevata" (Energy Drawn)
- "Energia Immessa" (Energy Fed)
- "Energia Prodotta" (Energy Produced)
- "Fascia Oraria Attuale" (Current Time Band)
- "Tempo Residuo Distacco" (Disconnect Timer)
- "Data Evento" (Event Date)

## Important Patterns

### Error Handling

- Use custom exceptions: `SinapsiConnectionError`, `SinapsiModbusError`
- Helper functions in `api.py` for consistent error handling
- Raise exceptions instead of returning `False` for proper availability tracking

### Logging

- Use centralized logging helpers from `helpers.py`:
  - `log_debug(logger, context, message, **kwargs)`
  - `log_info(logger, context, message, **kwargs)`
  - `log_warning(logger, context, message, **kwargs)`
  - `log_error(logger, context, message, **kwargs)`
- Never use f-strings in logger calls (use `%s` formatting)
- Always include context parameter (function name)
- Format: `(function_name) [key=value]: message`

### Async/Await

- All coordinator methods are async
- API methods use async/await properly
- Config entry methods follow HA conventions:
  - `add_update_listener()` - sync
  - `async_on_unload()` - sync (despite the name)
  - `async_forward_entry_setups()` - async
  - `async_unload_platforms()` - async

### Data Storage

- Modern pattern: Use `config_entry.runtime_data` (not `hass.data[DOMAIN][entry_id]`)
- `runtime_data` is typed with `RuntimeData` dataclass
- Automatically cleaned up on unload

## Code Quality Standards

### Ruff Configuration

- Follow `.ruff.toml` rules strictly
- Key rules:
  - A001: Don't shadow builtins
  - TRY300: Move return/break outside try blocks
  - TRY301: Abstract raise statements to helpers
  - RET505: Remove unnecessary else after return
  - G004: Use `%s` not f-strings in logging
  - SIM222: Correct boolean logic

### Type Hints

- Add type hints to all classes and instance variables
- Use modern type syntax where possible
- Config entry type alias: `type SinapsiAlfaConfigEntry = ConfigEntry[RuntimeData]`

### Testing Approach

- Test with actual Alfa devices
- Verify all 24 sensors (20 from device + 4 calculated)
- Test calculated sensor formulas
- Verify Italian sensor names display correctly
- Test reload/unload scenarios
- Test availability tracking (device offline scenarios)

## Common Patterns

### Version Updates

When bumping version for **STABLE releases**, update ALL of these:

1. **Update `manifest.json`** - `"version": "X.Y.Z"`
2. **Update `const.py`** - `VERSION = "X.Y.Z"`
3. **Create COMPREHENSIVE release notes**: `docs/releases/vX.Y.Z.md`
   - **IMPORTANT**: Include ALL changes since last stable release
   - Review all beta release notes if applicable
   - Review all commits since last stable
   - Include all sections: What's Changed, Bug Fixes, Features, Breaking Changes, etc.
   - Use existing v0.5.0.md as template
4. **Update `CHANGELOG.md`** with version summary
   - Add new version section at top (below Unreleased)
   - Include emoji-enhanced section headers
   - Link to detailed release notes: `[docs/releases/vX.Y.Z.md](docs/releases/vX.Y.Z.md)`
   - Add comparison link at bottom
5. **Commit**: "Bump version to vX.Y.Z"
6. **Tag**: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
7. **Push**: `git push && git push --tags`
8. **Create GitHub release**: `gh release create vX.Y.Z --latest`

### Release Documentation Structure

The project follows industry best practices for release documentation:

#### Two Types of Release Notes

**1. Stable/Official Release Notes (e.g., v0.5.0)**
- **Scope**: ALL changes since previous stable release
- **Example**: v0.5.0 includes everything since v0.4.2
  - All beta improvements
  - All commits between releases
  - All dependency updates
- **Purpose**: Complete picture for users upgrading from last stable
- **Sections**: Comprehensive - all fixes, features, breaking changes, dependencies

**2. Beta Release Notes (e.g., v0.5.0-beta.1)**
- **Scope**: Only incremental changes in this beta
- **Example**: v0.5.0-beta.2 shows only what's new since beta.1
- **Purpose**: Help beta testers focus on what to test
- **Sections**: Incremental - new fixes, new features, testing focus

#### Documentation Files

- **`CHANGELOG.md`** (root) - Quick overview of all releases
  - Based on [Keep a Changelog](https://keepachangelog.com/) format
  - Summarized entries for each version
  - Links to detailed release notes
  - Comparison links for GitHub diffs

- **`docs/releases/`** - Detailed release notes
  - One file per version: `vX.Y.Z.md` or `vX.Y.Z-beta.N.md`
  - Comprehensive technical details for stable releases
  - Incremental details for beta releases
  - Upgrade instructions
  - Testing recommendations

- **`docs/releases/README.md`** - Release directory guide
  - Explains stable vs. beta documentation approach
  - Documents release workflow
  - Provides templates

### Configuration Parameters

- `host` - IP/hostname of Alfa device
- `port` - TCP port (default: 502)
- `scan_interval` - Polling frequency (default: 60s, range: 30-600)

### Entity Unique IDs

- Sensors: `{mac_address}_{sensor_key}` (e.g., "AA:BB:CC:DD:EE:FF_potenza_prelevata")
- Device identifier: `(DOMAIN, mac_address)`
- MAC address from device is used for all identifiers
- Changing host/IP does not affect entity IDs or historical data

### Modbus Register Types

- `uint16` - Single 16-bit register (power, time band, timer)
- `uint32` - Two consecutive registers (energy totals, event date)
- `calcolato` - Calculated from other sensors (not read from device)

## Git Workflow

### Commit Messages

- Use conventional commits style
- Always include Claude attribution:

  ```
  <commit message>

  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

### Branch Strategy

- Main branch: `master`
- Create tags for releases
- Use pre-release flag for beta versions

## Dependencies

- Home Assistant core (>= 2025.10.0)
- `pymodbus>=3.11.2` - Modbus TCP client library
- `getmac>=0.9.5` - MAC address detection
- Compatible with Python 3.13+

## Key Files to Review

- `const.py` - Constants, sensor definitions, and validation rules
- `helpers.py` - Shared utilities and logging helpers
- `api.py` - Modbus communication and device-specific logic
- `sensor.py` - Sensor entities including calculated sensors
- `CHANGELOG.md` - Release history overview
- `docs/releases/` - Detailed release notes
- `docs/releases/README.md` - Release documentation guidelines

## Sinapsi-Specific Considerations

### Sensor Count
- **Total**: 24 sensors
  - 20 sensors from Modbus registers
  - 4 calculated sensors

### Calculated Sensor Formulas
```python
# Power calculations
potenza_consumata = potenza_prelevata + potenza_prodotta - potenza_immessa
potenza_auto_consumata = potenza_prodotta - potenza_immessa

# Energy calculations
energia_consumata = energia_prelevata + energia_prodotta - energia_immessa
energia_auto_consumata = energia_prodotta - energia_immessa
```

### Time Band Sensors (F1-F6)
- Italian electricity pricing uses 6 time bands (fasce orarie)
- Daily energy readings per time band (12 sensors total: 6 prelevata + 6 immessa)
- Current time band sensor shows which band is active

### Special Values
- Disconnect timer: Show only if not INVALID_DISTACCO_VALUE (65535)
- Event date: Show only if not MAX_EVENT_VALUE (4294967294)

## Don't Do

- ❌ Use `hass.data[DOMAIN][entry_id]` - use `runtime_data` instead
- ❌ Shadow Python builtins
- ❌ Use f-strings in logging
- ❌ Forget to update VERSION in both manifest.json AND const.py
- ❌ Create partial release notes for stable releases (must include ALL changes since last stable)
- ❌ Change Italian sensor names (they're for local market)
- ❌ Modify Modbus register addresses without device documentation
- ❌ Break calculated sensor formulas
- ❌ Remove special value handling (INVALID_DISTACCO_VALUE, MAX_EVENT_VALUE)
- ❌ Create documentation files without user request

## Differences from ABB PowerOne Integration

While this integration shares architecture with ha-abb-powerone-pvi-sunspec:

### Different Device
- **Alfa**: Energy monitoring device (consumption + production)
- **ABB/PowerOne**: Solar inverter only

### Different Registers
- Alfa uses custom Modbus register map
- Different addresses and data structures

### Different Sensors
- Alfa: 24 sensors (with time bands F1-F6, calculated consumption)
- ABB: Inverter-specific sensors (DC/AC, MPPT)

### Market-Specific
- Italian sensor names
- Italian time band structure (F1-F6)
- Italian energy market features

### Shared Features
- Code quality standards
- Logging patterns
- Error handling approach
- Release documentation structure
- Modern HA patterns

## Release Documentation Best Practice

**Critical reminder**: When creating stable release documentation (e.g., v0.6.0):
1. Review CHANGELOG for all changes since last stable
2. Check docs/releases/ for all beta notes
3. Review all commits: `git log v0.5.0..HEAD`
4. Document EVERYTHING - users may skip all betas
5. Use v0.5.0.md as comprehensive template
6. Update both CHANGELOG.md and docs/releases/vX.Y.Z.md

**For beta releases**:
1. Document only incremental changes
2. Reference previous beta for context
3. Focus on testing areas
4. Use v0.5.0-beta.1.md as template
