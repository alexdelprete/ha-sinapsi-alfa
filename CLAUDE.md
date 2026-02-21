# Claude Code Development Guidelines

## Critical Initial Steps

> **MANDATORY: At the START of EVERY session, you MUST read this entire CLAUDE.md file.**
>
> This file contains project-specific directives, workflows, and patterns that override default behavior.
> Failure to read this file results in violations of mandatory workflows (e.g., missing release documentation),
> duplicated effort, and broken architectural patterns.

**At every session start, you MUST:**

1. **Read this entire CLAUDE.md file** for project context and mandatory procedures
2. Review recent git commits to understand changes (`git log --oneline -10`)
3. Run `git status` to see uncommitted work

**Key mandatory workflows documented here:**

- Release documentation (CHANGELOG.md + docs/releases/)
- Version bumping (manifest.json + const.py)
- Logging patterns (helpers.py functions)
- Error handling (custom exceptions)
- Code quality checks (ruff, ty)

### CI Workflow Status and Logs (Use `gh` CLI)

> **IMPORTANT**: Always use `gh` CLI for CI workflow status and logs - it's more efficient than GitHub MCP.

The project has 3 CI workflows: **Lint**, **Tests**, and **Validate**.

**List recent workflow runs:**

```bash
gh run list --repo alexdelprete/ha-sinapsi-alfa --limit 5
```

**Get workflow status for a specific run:**

```bash
gh run view <run_id> --repo alexdelprete/ha-sinapsi-alfa
```

**Get test coverage from Tests workflow logs:**

```bash
gh run view <run_id> --repo alexdelprete/ha-sinapsi-alfa --log 2>&1 | findstr "TOTAL"
```

**Example output:**

```text
TOTAL                                 851      5    190     16    98%
```

The coverage percentage is the last column (98% in this example).

**Quick one-liner to get latest Tests run coverage:**

```bash
# Get latest Tests run ID and fetch coverage
gh run list --repo alexdelprete/ha-sinapsi-alfa --limit 5 | findstr Tests
# Then use the run ID from the output
gh run view <run_id> --repo alexdelprete/ha-sinapsi-alfa --log 2>&1 | findstr "TOTAL"
```

## Project Overview

This is a Home Assistant custom integration for **Sinapsi Alfa** energy monitoring devices using Modbus TCP protocol.
The Alfa device monitors power/energy consumption and photovoltaic production directly from the energy provider's
OpenMeter 2.0.

This integration is based on and aligned with
[ha-abb-powerone-pvi-sunspec](https://github.com/alexdelprete/ha-abb-powerone-pvi-sunspec),
sharing similar architecture and code quality standards.

## Code Architecture

### Core Components

1. **`__init__.py`** - Integration lifecycle management

   - `async_setup_entry()` - Initialize coordinator and platforms
   - `async_unload_entry()` - Clean shutdown and resource cleanup
   - `async_migrate_entry()` - Config migration logic
   - Uses `runtime_data` for storing coordinator and update listener

1. **`api.py`** - Modbus TCP communication layer (using ModbusLink)

   - `SinapsiAlfaAPI` class handles all Modbus operations
   - Uses `AsyncModbusClient` and `AsyncTcpTransport` from ModbusLink
   - Reads device-specific registers (power, energy, time band data)
   - Implements connection management and timeout handling
   - Custom exception handling: `SinapsiConnectionError`, `SinapsiModbusError`

1. **`coordinator.py`** - Data update coordination

   - `SinapsiAlfaCoordinator` manages polling cycles
   - Handles data refresh from API
   - Error handling and retry logic
   - Enforces MAX_SCAN_INTERVAL constraints

1. **`config_flow.py`** - UI configuration (VERSION = 2)

   - ConfigFlow for initial setup (stores data + options separately)
   - OptionsFlowWithReload for runtime options (scan_interval, timeout) - auto-reloads
   - Reconfigure flow for connection settings (name, host, port, skip_mac_detection)
   - Uses `vol.Clamp()` for better UX
   - Uses `async_update_reload_and_abort()` for reconfigure

1. **`sensor.py`** - Entity platform

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

## Code Quality Standards

### Ruff Configuration

- Follow `pyproject.toml` ruff rules strictly (in `[tool.ruff]` section)
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

### Project-Specific Release Steps

This project extends the shared release workflow with these specifics:

- **Step 1**: Create/update release notes in `docs/releases/vX.Y.Z.md`
- **Step 4**: Also run `ty check` in addition to standard linting
- **Step 5**: Use `commit-commands:commit` skill for staging and committing
- **Step 11**: Use `gh release create vX.Y.Z --title ... --notes-file docs/releases/vX.Y.Z.md`
- **Step 12**: GitHub Actions auto-uploads `sinapsi_alfa.zip` asset

### Project-Specific Release Checklist Additions

In addition to the shared release readiness checklist:

- **Release notes file** (`docs/releases/vX.Y.Z.md`) must be created
- **Download badge** (MANDATORY) at top of every release note file
- Include ALL changes since last stable release
- Review commits: `git log vPREV..HEAD`

### Release Readiness Report (Before Tag and Release)

> **⛔ MANDATORY: When user commands "tag and release", display the Release Readiness Report (RRR).**
>
> This report gives the user visibility into CI status and test coverage before creating the release.

**Before creating the tag, check CI workflows and display:**

```markdown
## Release Readiness Report (RRR)

| Check | Status | Details |
|-------|--------|---------|
| **Lint** | ✅ success | 2026-01-16 |
| **Tests** | ✅ success | 2026-01-16 |
| **Validate** | ✅ success | 2026-01-16 |
| **Test Coverage** | ✅ 98% | Minimum required: 97% |
| **Version** | 1.2.7 | manifest.json + const.py |
| **Working Tree** | ✅ Clean | No uncommitted changes |

All checks passed. Ready for release when you decide.
```

**Test Coverage Requirement:**

> **⚠️ CRITICAL: Test coverage MUST be at minimum 97%.**
> If coverage drops below 97%, flag it as ❌ and do not proceed with release until fixed.

**How to get test coverage:**

1. Get the Tests workflow run ID from `mcp__GitHub_MCP_Remote__actions_list`
2. Run: `gh run view <run_id> --repo alexdelprete/ha-sinapsi-alfa --log 2>&1 | grep "TOTAL"`
3. Parse the percentage from the output (last column)

**If CI is still running:**

```markdown
## Release Readiness Report (RRR)

| Check | Status | Details |
|-------|--------|---------|
| **Lint** | ⏳ in_progress | Started 2026-01-16 |
| **Tests** | ⏳ queued | Waiting... |
| **Validate** | ⏳ in_progress | Started 2026-01-16 |

CI workflows still running. Check back in 1-2 minutes.
```

### Issue References in Release Notes

When a release fixes a specific GitHub issue:

- Reference the issue number in release notes (e.g., "Fixes #178")
- Thank the user who opened the issue by name and GitHub handle
- **NEVER close the issue** - the user will do it manually

### After Publishing

1. Immediately bump to next version
1. Create new release notes file for next version
1. Mark previous version's documentation as frozen

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

Following HA best practices, configuration is split between `data` (initial config) and `options` (runtime tuning):

### Stored in `config_entry.data` (changed via Reconfigure flow)

- `name` - Device name (used for sensor prefix)
- `host` - IP/hostname of Alfa device
- `port` - TCP port (default: 502)
- `skip_mac_detection` - Use host-based ID instead of MAC (default: false)

### Stored in `config_entry.options` (changed via Options flow)

- `scan_interval` - Polling frequency (default: 60s, range: 30-600)
- `timeout` - Connection timeout in seconds (default: 10s, range: 5-60)

### Config Entry Migration

Version 1 → 2 migration moves `scan_interval` and `timeout` from `data` to `options`. The `async_migrate_entry()` function in `__init__.py` handles this automatically for existing installations.

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
- `modbuslink>=1.4.1` - Modern Modbus TCP client library (native async)
- `getmac>=0.9.5` - MAC address detection
- Compatible with Python 3.13+

### Dependency Update Checklist

**Before updating any dependency version in `manifest.json`:**

1. Verify the new version exists on PyPI: `https://pypi.org/project/PACKAGE_NAME/`
1. Check release notes for breaking changes
1. Test locally if possible

> **⚠️ IMPORTANT**: Always verify PyPI availability before committing dependency updates. We've had issues where
> upstream maintainers created GitHub releases but forgot to publish to PyPI, breaking our integration for users.

### Note on ModbusLink

As of v1.0.0, this integration uses [ModbusLink](https://github.com/Miraitowa-la/ModbusLink) instead of pymodbus:

- **Modern async API**: Native asyncio with context manager support
- **Cleaner code**: No need for separate payload decoder classes
- **Direct register access**: `read_holding_registers()` returns `List[int]` directly
- **Built-in error handling**: Exceptions raised automatically on errors
- **Configurable language**: Use `set_language(Language.EN)` for English-only logs AND errors

**Documentation Tip**: ModbusLink docs are best viewed in the repository:
[https://github.com/Miraitowa-la/ModbusLink/tree/master/docs/en](https://github.com/Miraitowa-la/ModbusLink/tree/master/docs/en)

See `docs/analysis/modbuslink-migration-analysis.md` for detailed migration documentation.

### Upstream Issues to Watch

Monitor these ModbusLink issues for potential improvements:

- **[#3](https://github.com/Miraitowa-la/ModbusLink/issues/3)** (Enhancement, Medium) - Replace manual
  `_extract_uint16()`/`_extract_uint32()` in `api.py:451-475` with native methods when available
- **[#4](https://github.com/Miraitowa-la/ModbusLink/issues/4)** (Bug, High) - Test parallel batch reads with
  `asyncio.gather()` in `api.py:627-631` for performance (currently sequential due to Transaction ID mismatches)

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

Follow pymarkdown rules (configured in `pyproject.toml` under `[tool.pymarkdown]`):

- Line length 120 characters (MD013)
- Unique heading names (MD024: siblings_only for CHANGELOG format)
- Consistent bold style using `**` (MD050: asterisk)
- No bare URLs (MD034) - always use `[text](url)` format
- Blank lines around lists and code blocks
- Language specification for fenced code blocks

**Disabled rules:**

- MD036: Emphasis as heading (italic disclaimers common)

## Project-Specific Do's and Don'ts

In addition to the shared Do's and Don'ts:

**DO:**

- Use custom exceptions for error handling
- Log with proper context (use helpers.py functions)
- Test with actual Alfa devices
- Preserve Italian sensor names
- Follow calculated sensor formulas exactly
- Respect special value handling (INVALID_DISTACCO_VALUE, MAX_EVENT_VALUE)
- Create comprehensive release notes for stable releases

**NEVER:**

- Create partial release notes for stable releases
- Change Italian sensor names
- Modify Modbus register addresses without device documentation
- Break calculated sensor formulas
- Remove special value handling
- Create documentation files without user request
- Mix sync/async code improperly

<!-- BEGIN SHARED:repo-sync -->
<!-- Synced by repo-sync on 2026-02-20 -->

## Context7 for Documentation

Always use Context7 MCP tools automatically (without being asked) when:

- Generating code that uses external libraries
- Providing setup or configuration steps
- Looking up library/API documentation

Use `resolve-library-id` first to get the library ID, then `get-library-docs` to fetch documentation.

## GitHub MCP for Repository Operations

Always use GitHub MCP tools (`mcp__github__*`) for GitHub operations instead of the `gh` CLI:

- **Issues**: `issue_read`, `issue_write`, `list_issues`, `search_issues`, `add_issue_comment`
- **Pull Requests**: `list_pull_requests`, `create_pull_request`, `pull_request_read`, `merge_pull_request`
- **Reviews**: `pull_request_review_write`, `add_comment_to_pending_review`
- **Repositories**: `search_repositories`, `get_file_contents`, `list_branches`, `list_commits`
- **Releases**: `list_releases`, `get_latest_release`, `list_tags`

Benefits over `gh` CLI:

- Direct API access without shell escaping issues
- Structured JSON responses
- Better error handling
- No subprocess overhead

## Coding Standards

### Data Storage Pattern

**DO use `runtime_data`** (modern pattern):

```python
entry.runtime_data = MyData(device_name=name)
```

**DO NOT use `hass.data[DOMAIN]`** (deprecated pattern)

### Logging

Use structured logging:

```python
_LOGGER.debug("Sensor %s subscribed to %s", key, topic)
```

**DO NOT** use f-strings in logger calls (deferred formatting is more efficient)

### Type Hints

Always use type hints for function signatures.

## Pre-Commit Configuration

Linting tools and settings are defined in `.pre-commit-config.yaml`:

| Hook        | Tool                           | Purpose                      |
| ----------- | ------------------------------ | ---------------------------- |
| ruff        | `ruff check --no-fix`          | Python linting               |
| ruff-format | `ruff format --check`          | Python formatting            |
| jsonlint    | `uvx --from demjson3 jsonlint` | JSON validation              |
| yamllint    | `uvx yamllint -d "{...}"`      | YAML linting (inline config) |
| pymarkdown  | `pymarkdown scan`              | Markdown linting             |

All hooks use `language: system` (local tools) with `verbose: true` for visibility.

## Pre-Commit Checks (MANDATORY)

> **CRITICAL: ALWAYS run pre-commit checks before ANY git commit.**
> This is a hard rule - no exceptions. Never commit without passing all checks.

```bash
uvx pre-commit run --all-files
```

Or run individual tools:

```bash
# Python formatting and linting
ruff format .
ruff check . --fix

# Markdown linting
pymarkdown scan .
```

All checks must pass before committing. This applies to ALL commits, not just releases.

### Windows Shell Notes

When running shell commands on Windows, stray `nul` files may be created (Windows null device artifact).
Check for and delete them after command execution:

```bash
rm nul  # if it exists
```

## Testing

> **CRITICAL: NEVER run pytest locally. The local environment cannot be set up correctly for
> Home Assistant integration tests. ALWAYS use GitHub Actions CI to run tests.**

To run tests:

1. Commit and push changes to the repository
1. GitHub Actions will automatically run the test workflow
1. Check the workflow results in the Actions tab or use `mcp__github__*` tools

> **CRITICAL: NEVER modify production code to make tests pass. Always fix the tests instead.**
> Production code is the source of truth. If tests fail, the tests are wrong - not the production code.
> The only exception is when production code has an actual bug that tests correctly identified.

## Quality Scale Tracking (MUST DO)

This integration tracks [Home Assistant Quality Scale][qs] rules in `quality_scale.yaml`.

**When implementing new features or fixing bugs:**

1. Check if the change affects any quality scale rules
1. Update `quality_scale.yaml` status accordingly:
   - `done` - Rule is fully implemented
   - `todo` - Rule needs implementation
   - `exempt` with `comment` - Rule doesn't apply (explain why)
1. Aim to complete all Bronze tier rules first, then Silver, Gold, Platinum

[qs]: https://developers.home-assistant.io/docs/core/integration-quality-scale/

## Release Management - CRITICAL

> **STOP: NEVER create git tags or GitHub releases without explicit user command.**
> This is a hard rule. Always stop after commit/push and wait for user instruction.

**Published releases are FROZEN** - Never modify documentation for released versions.

**Master branch = Next Release** - All commits target the next version with version bumped
in manifest.json and const.py.

### Version Bumping Rules

> **IMPORTANT: Do NOT bump version during a session. All changes go into the CURRENT unreleased version.**

- The version in `manifest.json` and `const.py` represents the NEXT release being prepared
- **NEVER bump version until user commands "tag and release"**
- Multiple features/fixes can be added to the same unreleased version
- Only bump to a NEW version number AFTER the current version is released

### Version Locations (Must Be Synchronized)

1. `custom_components/sinapsi_alfa/manifest.json` → `"version": "X.Y.Z"`
1. `custom_components/sinapsi_alfa/const.py` → `VERSION = "X.Y.Z"`

### Complete Release Workflow

> **IMPORTANT: Version Validation**
> The release workflow VALIDATES that tag, manifest.json, and const.py versions all match.
> You MUST update versions BEFORE creating the release, not after.

| Step | Tool           | Action                                                                  |
| ---- | -------------- | ----------------------------------------------------------------------- |
| 1    | Edit           | Update `CHANGELOG.md` with version summary                              |
| 2    | Edit           | Ensure `manifest.json` and `const.py` have correct version              |
| 3    | Bash           | Run linting: `uvx pre-commit run --all-files`                           |
| 4    | Bash           | `git add . && git commit -m "..."`                                      |
| 5    | Bash           | `git push`                                                              |
| 6    | **STOP**       | Wait for user "tag and release" command                                 |
| 7    | **CI Check**   | Verify ALL CI workflows pass (see CI Verification below)                |
| 8    | **Checklist**  | Display Release Readiness Checklist (see below)                         |
| 9    | Bash           | `git tag -a vX.Y.Z -m "Release vX.Y.Z"`                                |
| 10   | Bash           | `git push --tags`                                                       |
| 11   | gh CLI         | `gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(RELEASE_NOTES)"` |
| 12   | GitHub Actions | Validates versions match, then auto-uploads ZIP asset                   |
| 13   | Edit           | Bump versions in `manifest.json` and `const.py` to next version         |

### CI Verification (MANDATORY)

> **CRITICAL: Before tagging/releasing, ALWAYS verify ALL CI workflows are passing.**
> Use GitHub MCP tools to list workflow runs, then use `gh` CLI to get detailed logs if needed.
> NEVER proceed if any workflow is failing.

**Verification steps:**

1. Use `mcp__GitHub_MCP_Remote__actions_list` to list recent workflow runs:

   ```text
   actions_list(method="list_workflow_runs", owner="alexdelprete", repo="ha-sinapsi-alfa")
   ```

1. Check that ALL workflows show `conclusion: "success"`:
   - Lint workflow
   - Validate workflow
   - Tests workflow

1. If any workflow is failing, use `gh` CLI to get detailed failure logs:

   ```bash
   # View failed run logs (replace <run_id> with actual ID from step 1)
   gh run view <run_id> --log-failed

   # Or view full logs for a specific run
   gh run view <run_id> --log
   ```

1. Fix failing tests/issues, commit, push, and re-verify before proceeding

### Release Notes Format (MANDATORY)

When creating a release, use this format for the release notes:

```markdown
# Release vX.Y.Z

[![GitHub Downloads](https://img.shields.io/github/downloads/alexdelprete/ha-sinapsi-alfa/vX.Y.Z/total?style=for-the-badge)](https://github.com/alexdelprete/ha-sinapsi-alfa/releases/tag/vX.Y.Z)

**Release Date:** YYYY-MM-DD

**Type:** [Major/Minor/Patch] release - Brief description.

## What's Changed

### ✨ Added
- Feature 1

### 🔄 Changed
- Change 1

### 🐛 Fixed
- Fix 1

**Full Changelog**: https://github.com/alexdelprete/ha-sinapsi-alfa/compare/vPREV...vX.Y.Z
```

### Release Readiness Checklist (MANDATORY)

> **When user commands "tag and release", ALWAYS display this checklist BEFORE proceeding.**

```markdown
## Release Readiness Checklist

| Item | Status |
|------|--------|
| Version in `manifest.json` | X.Y.Z |
| Version in `const.py` | X.Y.Z |
| CHANGELOG.md updated | Updated |
| GitHub Actions (lint/test/validate) | PASSING |
| Working tree clean | Clean |
| Git tag | vX.Y.Z created/pushed |
```

Verify ALL items before proceeding with tag creation. If any item fails, fix it first.

## Do's and Don'ts

**DO:**

- Run `uvx pre-commit run --all-files` before EVERY commit
- Read CLAUDE.md at session start
- Use `runtime_data` for data storage (not `hass.data[DOMAIN]`)
- Use `@callback` decorator for message handlers
- Log with `%s` formatting (not f-strings)
- Handle missing data gracefully
- Update both manifest.json AND const.py for version bumps
- Get approval before creating tags/releases

**NEVER:**

- Commit without running pre-commit checks first
- Modify production code to make tests pass - fix the tests instead
- Use `hass.data[DOMAIN][entry_id]` - use `runtime_data` instead
- Shadow Python builtins (A001)
- Use f-strings in logging (G004)
- Create git tags or GitHub releases without explicit user instruction
- Forget to update VERSION in both manifest.json AND const.py
- Use blocking calls in async context
- Close GitHub issues without explicit user instruction

<!-- END SHARED:repo-sync -->

---

## Release History

### v1.2.0 - Test Coverage & CI Improvements

**Date:** January 1, 2026

- Achieved 98% test coverage (api.py 97%, coordinator.py 100%, config_flow.py 100%)
- Added comprehensive test suite with 188+ tests
- Fixed type annotations and DeviceInfo typing
- Updated CI workflows with Codecov integration
- All changes are CI/testing improvements - no functional changes

### v1.1.0 - ModbusLink Migration

**Date:** December 2025

- Migrated from pymodbus to ModbusLink for modern async Modbus operations
- Native asyncio with context manager support
- Cleaner code without separate payload decoder classes
- English-only error messages with `set_language(Language.EN)`
- Protocol error recovery with early abort on cascade failures

### v1.0.0 - First Stable Release

**Date:** October 2025

- Full async I/O with ModbusLink
- Complete sensor coverage (24 sensors including 4 calculated)
- Options flow for runtime tuning (scan_interval, timeout)
- Reconfigure flow for connection settings
- Config entry migration (v1 → v2)
- Repair notifications for connection issues
- Italian time band support (F1-F6)

---

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
