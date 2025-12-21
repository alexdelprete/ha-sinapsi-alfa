# Claude Code Development Guidelines

## Critical Initial Steps

**At every session start, you MUST:**

1. Read this entire CLAUDE.md file for project context
2. Review recent git commits to understand changes
3. Run `git status` to see uncommitted work

Skipping these steps causes violations of mandatory workflows, duplicated effort, and broken architectural patterns.

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

2. **`api.py`** - Modbus TCP communication layer (using ModbusLink)
   - `SinapsiAlfaAPI` class handles all Modbus operations
   - Uses `AsyncModbusClient` and `AsyncTcpTransport` from ModbusLink
   - Reads device-specific registers (power, energy, time band data)
   - Implements connection management and timeout handling
   - Custom exception handling: `SinapsiConnectionError`, `SinapsiModbusError`

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

### Logging Best Practices

**DataUpdateCoordinator:** Just raise `UpdateFailed`, don't manually log - HA handles logging automatically.

**ConfigEntryNotReady:** HA logs automatically, don't log manually.

This prevents log spam during extended outages.

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

## Release Management - CRITICAL

> **⛔ STOP: NEVER create git tags or GitHub releases without explicit user command.**
> This is a hard rule. Always stop after commit/push and wait for user instruction.

**Published releases are FROZEN** - Never modify documentation for released versions.

**Master branch = Next Release** - All commits target the next version with version bumped in manifest.json and const.py.

### Version Bumping Rules

> **⚠️ IMPORTANT: Do NOT bump version during a session. All changes go into the CURRENT unreleased version.**

- The version in `manifest.json` and `const.py` represents the NEXT release being prepared
- **NEVER bump version until user commands "tag and release"**
- Multiple features/fixes can be added to the same unreleased version
- Only bump to a NEW version number AFTER the current version is released

**Example workflow:**
1. Current version is 1.1.8 (unreleased, after v1.1.7 was released)
2. User asks for fix A → Add fix A to v1.1.8, commit, push
3. User asks for fix B → Add fix B to v1.1.8 (same version!), commit, push
4. User says "tag and release" → Create v1.1.8 tag and release
5. After release: Bump version to 1.1.9 for next development cycle

### Complete Release Workflow

1. Create/update release notes in `docs/releases/vX.Y.Z.md`
   - **IMPORTANT**: Include ALL changes since last stable release
   - Review all beta release notes if applicable
   - Review all commits since last stable: `git log vX.Y.Z..HEAD`
   - Include all sections: What's Changed, Bug Fixes, Features, Breaking Changes, etc.
2. Update `CHANGELOG.md` with version summary
   - Add new version section at top (below Unreleased)
   - Include emoji-enhanced section headers
   - Link to detailed release notes
   - Add comparison link at bottom
3. Commit changes
4. Push commits and verify clean state
5. **STOP - GET APPROVAL** before creating tags/releases
6. Only create tags/releases when explicitly instructed:
   - `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
   - `git push --tags`
   - `gh release create vX.Y.Z --latest`
7. **After release**: Bump versions in `manifest.json` and `const.py` to next version

**CRITICAL:** Never create git tags or GitHub releases without explicit user instruction.

### Issue References in Release Notes

When a release fixes a specific GitHub issue:

- Reference the issue number in release notes (e.g., "Fixes #178")
- Thank the user who opened the issue by name and GitHub handle
- **NEVER close the issue** - the user will do it manually

### After Publishing

1. Immediately bump to next version
2. Create new release notes file for next version
3. Mark previous version's documentation as frozen

### Release Documentation Structure

The project follows industry best practices for release documentation:

#### Stable/Official Release Notes (e.g., v0.5.0)

- **Scope**: ALL changes since previous stable release
- **Example**: v0.5.0 includes everything since v0.4.2
- **Purpose**: Complete picture for users upgrading from last stable
- **Sections**: Comprehensive - all fixes, features, breaking changes, dependencies

#### Beta Release Notes (e.g., v0.5.0-beta.1)

- **Scope**: Only incremental changes in this beta
- **Example**: v0.5.0-beta.2 shows only what's new since beta.1
- **Purpose**: Help beta testers focus on what to test
- **Sections**: Incremental - new fixes, new features, testing focus

### Documentation Files

- **`CHANGELOG.md`** (root) - Quick overview of all releases based on Keep a Changelog format
- **`docs/releases/`** - Detailed release notes (one file per version)
- **`docs/releases/README.md`** - Release directory guide and templates

## Git Workflow

### Commit Messages

Use conventional commits with Claude attribution:

```text
feat(api): implement new feature

[Description]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Branch Strategy

- Main branch: `master`
- Create tags for releases
- Use pre-release flag for beta versions

## Configuration Parameters

- `host` - IP/hostname of Alfa device
- `port` - TCP port (default: 502)
- `scan_interval` - Polling frequency (default: 60s, range: 30-600)
- `timeout` - Connection timeout in seconds (default: 10s, range: 5-60)

## Entity Unique IDs

- Sensors: `{mac_address}_{sensor_key}` (e.g., "AA:BB:CC:DD:EE:FF_potenza_prelevata")
- Device identifier: `(DOMAIN, mac_address)`
- MAC address from device is used for all identifiers
- Changing host/IP does not affect entity IDs or historical data

## Modbus Register Types

- `uint16` - Single 16-bit register (power, time band, timer)
- `uint32` - Two consecutive registers (energy totals, event date)
- `calcolato` - Calculated from other sensors (not read from device)

## Dependencies

- Home Assistant core (>= 2025.10.0)
- `modbuslink>=1.3.1` - Modern Modbus TCP client library (native async)
- `getmac>=0.9.5` - MAC address detection
- Compatible with Python 3.13+

### Note on ModbusLink

As of v1.0.0, this integration uses [ModbusLink](https://github.com/Miraitowa-la/ModbusLink) instead of pymodbus:

- **Modern async API**: Native asyncio with context manager support
- **Cleaner code**: No need for separate payload decoder classes
- **Direct register access**: `read_holding_registers()` returns `List[int]` directly
- **Built-in error handling**: Exceptions raised automatically on errors
- **Configurable logging language**: Use `ModbusLogger.setup_logging(language=Language.EN)` for English-only logs

**Documentation Tip**: ModbusLink docs are best viewed in the repository:
[https://github.com/Miraitowa-la/ModbusLink/tree/master/docs/en](https://github.com/Miraitowa-la/ModbusLink/tree/master/docs/en)

See `docs/analysis/modbuslink-migration-analysis.md` for detailed migration documentation.

### Upstream Issues to Watch

Monitor these ModbusLink issues for potential improvements:

| Issue | Type | Impact | Action When Fixed |
|-------|------|--------|-------------------|
| [#3](https://github.com/Miraitowa-la/ModbusLink/issues/3) | Enhancement | Medium | Replace manual `_extract_uint16()`/`_extract_uint32()` in api.py with native `read_uint32()` etc. |
| [#4](https://github.com/Miraitowa-la/ModbusLink/issues/4) | Bug | High | Test parallel batch reads with `asyncio.gather()` in `read_modbus_alfa()` for performance improvement |

**Current workarounds:**

- Issue #3: Manual extraction methods in `api.py:451-475`
- Issue #4: Sequential batch reads in `api.py:627-631` (comment: "parallel causes Transaction ID mismatches")

## Key Files to Review

- `const.py` - Constants, sensor definitions, and validation rules
- `helpers.py` - Shared utilities and logging helpers
- `api.py` - ModbusLink communication and device-specific logic
- `sensor.py` - Sensor entities including calculated sensors
- `CHANGELOG.md` - Release history overview
- `docs/releases/` - Detailed release notes
- `docs/releases/README.md` - Release documentation guidelines
- `docs/analysis/modbuslink-migration-analysis.md` - ModbusLink migration documentation

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

## Markdown Standards

Follow markdownlint rules (configured in `.markdownlint.json`):

- Blank lines around lists and code blocks
- Language specification for fenced code blocks
- Blank line after bold headers
- Unique heading names (MD024: siblings_only for CHANGELOG format)
- Line length 120 characters (MD013)
- No bare URLs (MD034) - always use `[text](url)` format
- Consistent bold style using `**` (MD050: asterisk)

**Disabled rules** (common patterns in GitHub READMEs):

- MD013: Line length (URLs and images often exceed limits)
- MD025: Single h1 (multiple `#` sections common in READMEs)
- MD001: Heading increment (flexible heading hierarchy)
- MD036: Emphasis as heading (italic disclaimers common)

## Do's and Don'ts

**✅ DO:**

- Read CLAUDE.md at session start
- Use custom exceptions for error handling
- Log with proper context (use helpers.py functions)
- Use `runtime_data` for data storage
- Handle missing data gracefully
- Test with actual Alfa devices
- Preserve Italian sensor names
- Follow calculated sensor formulas exactly
- Respect special value handling (INVALID_DISTACCO_VALUE, MAX_EVENT_VALUE)
- Update both manifest.json AND const.py for version bumps
- Create comprehensive release notes for stable releases
- Get approval before creating tags/releases

**❌ NEVER:**

- Use `hass.data[DOMAIN][entry_id]` - use `runtime_data` instead
- Shadow Python builtins
- Use f-strings in logging
- Forget to update VERSION in both manifest.json AND const.py
- Create partial release notes for stable releases
- Change Italian sensor names
- Modify Modbus register addresses without device documentation
- Break calculated sensor formulas
- Remove special value handling
- Create documentation files without user request
- Mix sync/async code improperly
- Use blocking calls in async context
- Close GitHub issues without explicit user instruction
- Create git tags or GitHub releases without explicit user instruction

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
