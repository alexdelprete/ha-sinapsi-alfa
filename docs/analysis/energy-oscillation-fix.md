# Energy Oscillation Fix: Synchronized Derived Calculation

**Date**: February 2026
**Author**: Claude Code Analysis
**Status**: Implemented (v1.2.13)

## Executive Summary

The Alfa firmware updates `energia_prodotta` and `energia_immessa` registers asynchronously on a
~15-minute internal cycle, with prodotta always updating ~1 minute before immessa. Our 60s polling
captures them on alternating polls, causing calculated sensors (`energia_auto_consumata`,
`energia_consumata`) to oscillate. HA's `TOTAL_INCREASING` state class treats each dip as a meter
reset, resulting in **~264% over-counting** on daily self-consumption.

**Fix**: Only recalculate cumulative energy sensors when both base sensors have updated since the
last calculation, with a 2-poll timeout fallback for single-sensor-changing periods.

______________________________________________________________________

## Problem Description

### Observed Symptoms

- `sensor.alfa_energy_self_consumed` shows a sawtooth oscillation pattern
- Daily self-consumption reports ~15 kWh when the real value is ~4 kWh
- Utility meters tracking calculated sensors accumulate inflated values
- Direct Modbus sensors (production, export, import) are unaffected

### Root Cause: Asynchronous Firmware Register Updates

The Alfa device maintains internal counters for `energia_prodotta` (production) and
`energia_immessa` (export). These counters are updated on a ~15-minute cycle, but
**prodotta always updates ~1 minute before immessa**.

With a 60-second polling interval, this creates an alternating capture pattern:

```text
Time     | Poll | energia_prodotta | energia_immessa | Calculated (P - I)
---------|------|------------------|-----------------|--------------------
14:14:00 | N    | 27286.53 (NEW)   | 974.49 (old)    | 26312.04 ↑ spike
14:15:00 | N+1  | 27286.53 (same)  | 974.57 (NEW)    | 26311.96 ↓ dip
14:29:00 | N+2  | 27286.78 (NEW)   | 974.57 (old)    | 26312.21 ↑ spike
14:30:00 | N+3  | 27286.78 (same)  | 975.45 (NEW)    | 26311.33 ↓ dip
```

### Why TOTAL_INCREASING Causes Double-Counting

HA's `TOTAL_INCREASING` state class is designed for monotonically increasing meters (like utility
meters). When a value decreases, HA interprets it as a "meter reset" — the old meter was replaced
and counting restarted from zero. HA then adds the new value to the accumulated total:

```text
accumulated += new_value  (after reset)
```

With the sawtooth pattern above, every dip triggers a "reset", and every subsequent spike gets
added in full. This compounds across the ~96 daily update cycles (every 15 minutes × 24 hours),
producing ~264% over-counting.

### Data Analysis (Feb 16-23, 2026)

Analysis of one week of HA history data confirmed:

- The alternating pattern is **consistent firmware behavior**, not intermittent
- Prodotta always updates first, immessa follows on the next poll
- The pattern occurs every ~15 minutes during daylight/production hours
- During no-export periods (nighttime), only prodotta changes — no oscillation

______________________________________________________________________

## Solution: Synchronized Calculation with Timeout Fallback

### Design Principles

1. **Energy sensors** (`TOTAL_INCREASING`): Wait for both base sensors to update before
   recalculating — this guarantees a synchronized pair and eliminates oscillation
2. **Power sensors** (`MEASUREMENT`): Always calculate immediately — instantaneous oscillations
   are normal and don't cause accumulation errors
3. **Timeout fallback**: If only one sensor changes for `SYNC_TIMEOUT_POLLS` consecutive polls,
   calculate anyway — this handles no-export periods safely (no oscillation risk when only one
   sensor is changing)

### Implementation

**Files modified:**

- `const.py` — Added `SYNC_TIMEOUT_POLLS = 2` constant
- `api.py` — Replaced `_calculate_derived_values()` with synchronized logic, added 3 tracking
  instance variables (`_last_calc_prodotta`, `_last_calc_immessa`, `_unsync_poll_count`)

### Algorithm

```text
On each poll:
  1. Always calculate power sensors (potenza_*)
  2. Compare current energia_prodotta/immessa with last-calculated values
  3. If first poll (no previous data) → calculate
  4. If both changed → calculate immediately, reset counter
  5. If exactly one changed → increment counter
     - If counter >= SYNC_TIMEOUT_POLLS → calculate, reset counter
     - Otherwise → skip, keep previous energy values
  6. If neither changed → reset counter to 0 (no new data)
```

### Behavior by Scenario

| Scenario | Behavior | Result |
|----------|----------|--------|
| First poll after startup | Always calculates | Baseline established |
| Both sensors updated | Immediate recalculation | Synchronized, accurate |
| Only prodotta updated (poll 1/2) | Skip calculation | Prevents spike |
| Only prodotta updated (poll 2/2) | Timeout → calculate | Safe: no alternation pattern |
| Only immessa updated | Same as above | Same timeout logic |
| Neither changed | Counter resets to 0 | No new data, no action needed |
| No-export period (immessa constant) | Timeout every 2 polls | Correct: prodotta - constant |
| Device reboot (zeroed registers) | Base sensors protected by reboot check | Derived uses protected values |

### Why SYNC_TIMEOUT_POLLS = 2

The Alfa firmware's ~15-minute cycle with ~1-minute offset means:

- **Normal alternation**: Prodotta on poll N, immessa on poll N+1 → both fresh on poll N+1
- **Timeout = 2**: If only one sensor changes for 2 consecutive polls, it means the other genuinely
  isn't changing (e.g., no export). Safe to calculate because there's no alternating pattern
- **Timeout = 1** would be too aggressive: could trigger on the first unsync poll before the
  second sensor has a chance to update

______________________________________________________________________

## Affected Sensors and Utility Meters

### Directly Fixed (Integration Sensors)

| Sensor | State Class | Fix |
|--------|-------------|-----|
| `energia_auto_consumata` | TOTAL_INCREASING | Synchronized calculation |
| `energia_consumata` | TOTAL_INCREASING | Synchronized calculation |
| `potenza_auto_consumata` | MEASUREMENT | Unchanged (always calculated) |
| `potenza_consumata` | MEASUREMENT | Unchanged (always calculated) |

### Affected Utility Meters (12 Sensors)

Utility meters tracking the two calculated energy sensors accumulate inflated values:

- Consumption (x6): `sensor.{hourly,daily,weekly,monthly,yearly,total}_energy_consumption`
- Autoconsumption (x6): `sensor.{hourly,daily,weekly,monthly,yearly,total}_energy_autoconsumption`

### NOT Affected (18 Sensors)

Utility meters tracking direct Modbus sensors are correct — their source sensors don't oscillate:

- Production (x6): `sensor.{hourly,daily,...}_energy_production`
- Export (x6): `sensor.{hourly,daily,...}_energy_export`
- Import (x6): `sensor.{hourly,daily,...}_energy_import`

### Remediation Steps for Utility Meters

After deploying the fix, future data is automatically correct. To fix historical data:

1. **Calibrate today's values** using `utility_meter.calibrate`:

   ```yaml
   service: utility_meter.calibrate
   data:
     value: "<correct_value>"
   target:
     entity_id: sensor.daily_energy_autoconsumption
   ```

   Correct value = daily_production - daily_export (e.g., 15.41 - 11.00 = 4.41 kWh)

2. **Fix historical statistics** via Developer Tools > Statistics:
   - Search for affected sensor entities
   - Click the adjust icon to correct individual data points
   - Both short-term and long-term statistics tables need correction

______________________________________________________________________

## Verification

After deployment, verify the fix by monitoring:

1. **`sensor.alfa_energy_self_consumed`** — Should increase monotonically, no sawtooth pattern
2. **`sensor.daily_energy_autoconsumption`** — Should show realistic values (~4-5 kWh, not ~15 kWh)
3. **Debug logs** — Look for "Skipping energy calc" messages confirming sync logic is active
4. **Peak sun hours** — Verify the alternating pattern is handled correctly
5. **Early morning (no export)** — Verify the timeout fallback allows updates

______________________________________________________________________

## Test Coverage

The `TestSynchronizedEnergyCalculation` class in `tests/test_api.py` covers:

- First poll always calculates (no previous tracking data)
- Both sensors fresh → immediate recalculation
- Only prodotta fresh → skip (wait for immessa)
- Only immessa fresh → skip (wait for prodotta)
- Timeout fallback after SYNC_TIMEOUT_POLLS
- Neither changed → timeout then calculate (harmless)
- Full oscillation prevention with real alternating data from Feb 23
- No-export period with timeout allowing updates
- Power sensors always calculated regardless of sync state
- Sync counter resets when both sensors become fresh
