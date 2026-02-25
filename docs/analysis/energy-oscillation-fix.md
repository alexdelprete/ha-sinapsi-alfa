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

**Fix**: `energia_auto_consumata` (prodotta - immessa) is only recalculated when both base sensors
have updated since the last calculation, with a 3-poll timeout fallback for single-sensor-changing
periods. `energia_consumata` (auto_consumata + prelevata) is always recalculated because it depends
on `prelevata` which changes independently every poll.

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

- `const.py` — Added `SYNC_TIMEOUT_POLLS = 3` constant
- `api.py` — Replaced `_calculate_derived_values()` with synchronized logic, added 3 tracking
  instance variables (`_last_calc_prodotta`, `_last_calc_immessa`, `_unsync_poll_count`)

### Algorithm

```text
On each poll:
  1. Always calculate power sensors (potenza_*)
  2. Compare current energia_prodotta/immessa with last-calculated values
  3. If first poll (no previous data) → calculate energia_auto_consumata
  4. If both changed → calculate energia_auto_consumata immediately, reset counter
  5. If exactly one changed → increment counter
     - If counter >= SYNC_TIMEOUT_POLLS → calculate energia_auto_consumata, reset counter
     - Otherwise → skip energia_auto_consumata, log waiting state
  6. If neither changed → reset counter to 0, then:
     - If auto_consumata != prodotta - immessa (gap > 0.001) →
       reconcile auto_consumata to true value (quiescent reconciliation)
     - Otherwise → no-op (already aligned)
  7. Always recalculate energia_consumata = auto_consumata + prelevata
     (prelevata changes independently of the prodotta/immessa sync mechanism)
```

### Behavior by Scenario

| Scenario | auto_consumata | consumata | Result |
|----------|----------------|-----------|--------|
| First poll after startup | Calculated | Calculated | Baseline established |
| Both sensors updated | Recalculated | Recalculated | Synchronized, accurate |
| Only prodotta updated (1/3) | Frozen | Recalculated | Prevents spike in auto, consumata tracks prelevata |
| Only prodotta updated (2/3) | Frozen | Recalculated | Extra poll gives immessa time to catch up |
| Only prodotta updated (3/3) | Timeout → calc | Recalculated | Safe: no alternation pattern |
| Only immessa updated | Same as above | Recalculated | Same timeout logic |
| Neither changed (idle, aligned) | Unchanged | Recalculated | No-op, counter resets to 0 |
| Neither changed (idle, gap) | Reconciled | Recalculated | Quiescent reconciliation flushes residual gap |
| Only prelevata changes (night) | Frozen | Recalculated | consumata tracks grid import growth |
| No-export period | Timeout every 3 polls | Recalculated | Correct: prodotta - constant |
| Device reboot | Protected by reboot check | Recalculated | Derived uses protected values |

### Why SYNC_TIMEOUT_POLLS = 3

The Alfa firmware's ~15-minute cycle with ~1-minute offset means:

- **Normal alternation**: Prodotta on poll N, immessa on poll N+1 → both fresh on poll N+1
- **Timeout = 3**: Gives immessa safe margin to catch up with prodotta. With 60s polling and
  ~60s firmware delay, immessa should be caught on poll N+1 (both fresh). The extra poll
  before timeout prevents the overshoot-dip cycle that occurs when timeout fires with stale
  immessa — TOTAL_INCREASING treats the subsequent dip as a reset, overcounting by the
  export increment each firmware cycle
- **Timeout = 2** was too aggressive: with borderline firmware timing (>60s delay), the timeout
  could fire on poll N+1 before immessa updated. This produced overcount = daily export.
- **Timeout = 1** would be even worse: triggers on the first unsync poll before the second
  sensor has any chance to update

______________________________________________________________________

## Affected Sensors and Utility Meters

### Directly Fixed (Integration Sensors)

| Sensor | State Class | Strategy |
|--------|-------------|----------|
| `energia_auto_consumata` | TOTAL_INCREASING | Synchronized (inside sync guard) |
| `energia_consumata` | TOTAL_INCREASING | Always recalculated (depends on prelevata) |
| `potenza_auto_consumata` | MEASUREMENT | Always calculated (instantaneous) |
| `potenza_consumata` | MEASUREMENT | Always calculated (instantaneous) |

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
3. **Debug logs** — Look for "Waiting for synchronized base sensor update" messages (only when
   one sensor is fresh, not on idle polls)
4. **Peak sun hours** — Verify the alternating pattern is handled correctly
5. **Early morning (no export)** — Verify the timeout fallback allows updates
6. **Nighttime (no production)** — Verify `energia_consumata` keeps updating as `prelevata` grows

______________________________________________________________________

## Test Coverage

The `TestSynchronizedEnergyCalculation` class in `tests/test_api.py` covers:

- First poll always calculates (no previous tracking data)
- Both sensors fresh → immediate recalculation
- Only prodotta fresh → skip auto_consumata (wait for immessa)
- Only immessa fresh → skip auto_consumata (wait for prodotta)
- Timeout fallback after SYNC_TIMEOUT_POLLS
- Neither changed → counter resets, no unnecessary timeout
- Idle polls don't poison the unsync counter (beta.1 regression)
- Full oscillation prevention with real alternating data
- No-export period with timeout allowing updates (consumata verified)
- Power sensors always calculated regardless of sync state
- Sync counter resets when both sensors become fresh
- **consumata updates when only prelevata changes** (beta.3 critical fix)
- Night scenario: 10 polls with only prelevata growing
- Day-to-night transition: full lifecycle verification
- consumata uses latest prelevata after sync calc
- Debug log fires only when waiting (one sensor fresh), not on idle polls
