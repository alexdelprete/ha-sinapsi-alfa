# ModbusLink Migration Analysis

**Date**: December 2025
**Author**: Claude Code Analysis
**Status**: Planning Document

## Executive Summary

This document analyzes the feasibility of migrating the ha-sinapsi-alfa Home Assistant integration
from **pymodbus** to **ModbusLink** library.
The analysis includes a comprehensive pros/cons comparison and a detailed surgical migration plan.

### Decision

**Proceed with migration** - Accept early adopter risks in exchange for modern API benefits.

### Risk Acknowledgment

ModbusLink is currently in **Alpha status** (Development Status 3). This migration prioritizes modern API design over production stability guarantees. A rollback strategy is included.

______________________________________________________________________

## Library Comparison

| Aspect              | pymodbus              | ModbusLink |
| ------------------- | --------------------- | ---------- |
| **Version**         | 3.11.4                | 1.2.0      |
| **Status**          | Production/Stable (5) | Alpha (3)  |
| **Python**          | 3.10+                 | 3.9+       |
| **First Release**   | 2010+                 | July 2025  |
| **Maintainers**     | 3 active              | 1          |
| **GitHub Stars**    | 2000+                 | 3          |
| **HA Ecosystem**    | Widely used           | None       |
| **Async Support**   | Yes                   | Native     |
| **Context Manager** | Manual                | Built-in   |
| **Type Hints**      | Partial               | Full       |
| **Data Decoders**   | Deprecated            | Built-in   |

______________________________________________________________________

## Pros/Cons Analysis

### ModbusLink Advantages

1. **Modern Async API Design**

   - Native async context manager: `async with client:`
   - Designed from ground up for asyncio
   - No legacy synchronous code paths

1. **Built-in Data Type Methods**

   - `read_float32()`, `read_int32()`, `read_holding_registers()`
   - No need for separate payload decoder classes
   - Configurable byte/word ordering built-in

1. **Simplified Codebase**

   - Eliminates `pymodbus_payload.py` (516 lines)
   - Eliminates `pymodbus_constants.py` (147 lines)
   - Cleaner, more maintainable code

1. **Clean Exception Hierarchy**

   - `ModbusLinkError` (base)
   - `ConnectionError`, `TimeoutError`
   - `CRCError`, `InvalidResponseError`
   - `ModbusException`

1. **Full Type Hints**

   - Complete typing throughout library
   - Better IDE support and error detection

1. **Connection Pooling**

   - Built-in async connection pool management
   - Better resource utilization for high-frequency polling

### ModbusLink Risks (Acknowledged)

1. **Alpha Status** - Not officially production-ready
1. **Very New Library** - First release July 2025 (~5 months old)
1. **Minimal Adoption** - Only 3 GitHub stars
1. **Single Maintainer** - Bus factor = 1
1. **Limited Production Testing** - Not battle-tested
1. **No HA Ecosystem Usage** - No other Home Assistant integrations use it
1. **Documentation Gaps** - Some areas incomplete
1. **Unknown Edge Cases** - May have undiscovered bugs

### pymodbus Advantages

1. **Production Stable** - 10+ years of production use
1. **Large Community** - Extensive testing and bug reports
1. **HA Ecosystem Standard** - Used by many HA integrations
1. **Active Maintenance** - 3 maintainers, regular releases
1. **Comprehensive Documentation** - Well documented
1. **Known Behavior** - Edge cases are documented and handled

### pymodbus Disadvantages

1. **Deprecated APIs** - `BinaryPayloadDecoder` deprecated, requires local copies
1. **Verbose Syntax** - Requires manual payload handling and decoding
1. **Older API Design** - Not designed with modern async patterns in mind

______________________________________________________________________

## Current Implementation Analysis

### Files Using pymodbus

| File                                                                                | Lines | Usage                                         |
| ----------------------------------------------------------------------------------- | ----- | --------------------------------------------- |
| [api.py](../../custom_components/sinapsi_alfa/api.py)                               | 560   | Main Modbus communication                     |
| [pymodbus_constants.py](../../custom_components/sinapsi_alfa/pymodbus_constants.py) | 147   | Local copy of deprecated Endian enum          |
| [pymodbus_payload.py](../../custom_components/sinapsi_alfa/pymodbus_payload.py)     | 516   | Local copy of deprecated BinaryPayloadDecoder |

### Current Imports (api.py)

```python
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException
from .pymodbus_constants import Endian
from .pymodbus_payload import BinaryPayloadDecoder
```

### Current Connection Pattern

```python
# Initialization (line 105-107)
self._client = AsyncModbusTcpClient(
    host=self._host, port=self._port, timeout=self._timeout
)

# Connection (line 314-315)
async with self._lock:
    await self._client.connect()

# Check connected (line 323)
if not self._client.connected:
    raise SinapsiConnectionError(...)

# Close (line 283-284)
async with self._lock:
    self._client.close()
```

### Current Read Pattern

```python
# Read registers (line 361-364)
async with self._lock:
    result = await self._client.read_holding_registers(
        address=address, count=count, device_id=self._device_id
    )

# Check for errors (line 365-378)
if result.isError():
    raise SinapsiModbusError(...)
```

### Current Decoding Pattern

```python
# Decode registers (line 406-415)
decoder = BinaryPayloadDecoder.fromRegisters(
    read_data.registers, byteorder=Endian.BIG
)

if reg_type == "uint16":
    return round(float(decoder.decode_16bit_uint()), 2)
elif reg_type == "uint32":
    return round(float(decoder.decode_32bit_uint()), 2)
```

______________________________________________________________________

## Surgical Migration Plan

### Phase 1: Preparation

#### 1.1 Create Feature Branch

```bash
git checkout -b feature/modbuslink-migration
```

#### 1.2 Update Dependencies

**File**: `custom_components/sinapsi_alfa/manifest.json`

```json
{
  "requirements": ["modbuslink>=1.2.0", "getmac>=0.9.5"]
}
```

### Phase 2: API Refactoring

#### 2.1 Update Imports

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 14-16, 31-32

```python
# REMOVE
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException
from .pymodbus_constants import Endian
from .pymodbus_payload import BinaryPayloadDecoder

# ADD
from modbuslink import AsyncModbusClient, AsyncTcpTransport
from modbuslink import (
    ConnectionError as ModbusConnectionError,
    TimeoutError as ModbusTimeoutError,
    ModbusException,
)
```

#### 2.2 Update Class Attributes

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 73-74 (class docstring)

```python
# CHANGE
"""Thread safe wrapper class for pymodbus."""

# TO
"""Thread safe wrapper class for ModbusLink."""
```

#### 2.3 Update Client Initialization

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 105-108

```python
# REMOVE
self._client = AsyncModbusTcpClient(
    host=self._host, port=self._port, timeout=self._timeout
)

# ADD
self._transport = AsyncTcpTransport(
    host=self._host,
    port=self._port,
    timeout=self._timeout
)
self._client = AsyncModbusClient(self._transport)
```

#### 2.4 Update Connection Method

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 300-355 (`connect` method)

```python
async def connect(self):
    """Connect client."""
    log_debug(
        _LOGGER,
        "connect",
        "Connecting to device",
        host=self._host,
        port=self._port,
        timeout=self._timeout,
    )
    if await self.check_port():
        log_debug(_LOGGER, "connect", "Device ready for Modbus TCP connection")
        start_time = time.time()
        try:
            async with self._lock:
                await self._transport.open()
            connect_duration = time.time() - start_time
            log_debug(
                _LOGGER,
                "connect",
                "Connection attempt completed",
                duration_s=f"{connect_duration:.3f}",
            )
            # ModbusLink: check transport.is_open instead of client.connected
            if not self._transport.is_open:
                self._connection_healthy = False
                raise SinapsiConnectionError(
                    f"Failed to connect to {self._host}:{self._port}",
                    self._host,
                    self._port,
                )
            else:
                log_debug(_LOGGER, "connect", "Modbus TCP Client connected")
                self._connection_healthy = True
                return True
        except (ModbusConnectionError, ModbusTimeoutError) as e:
            self._connection_healthy = False
            log_error(
                _LOGGER,
                "connect",
                "Connection failed",
                error_type=type(e).__name__,
                error=e,
            )
            raise SinapsiConnectionError(
                f"Failed to connect: {e}",
                self._host,
                self._port,
            ) from e
    else:
        log_debug(_LOGGER, "connect", "Device not ready for Modbus TCP connection")
        self._connection_healthy = False
        raise SinapsiConnectionError(
            f"Device not active on {self._host}:{self._port}",
            self._host,
            self._port,
        )
```

#### 2.5 Update Close Method

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 278-298 (`close` method)

```python
async def close(self):
    """Disconnect client."""
    try:
        if self._transport.is_open:
            log_debug(_LOGGER, "close", "Closing Modbus TCP connection")
            async with self._lock:
                await self._transport.close()
                self._connection_healthy = False
                return True
        else:
            log_debug(_LOGGER, "close", "Modbus TCP connection already closed")
    except (ModbusConnectionError, ModbusTimeoutError) as connect_error:
        log_error(
            _LOGGER,
            "close",
            "Close connection error",
            error=connect_error,
        )
        raise SinapsiConnectionError(
            f"Connection failed: {connect_error}", self._host, self._port
        ) from connect_error
```

#### 2.6 Update Read Method

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 357-402 (`read_holding_registers` method)

```python
async def read_holding_registers(self, address: int, count: int) -> list[int]:
    """Read holding registers."""
    try:
        async with self._lock:
            result = await self._client.read_holding_registers(
                slave_id=self._device_id,
                start_address=address,
                quantity=count
            )
        # ModbusLink returns List[int] directly, raises on error
        return result
    except (ModbusConnectionError, ModbusTimeoutError) as connect_error:
        log_error(
            _LOGGER,
            "read_holding_registers",
            "Connection error",
            address=address,
            error=connect_error,
        )
        self._connection_healthy = False
        raise SinapsiConnectionError(
            f"Connection failed: {connect_error}", self._host, self._port
        ) from connect_error
    except ModbusException as modbus_error:
        log_error(
            _LOGGER,
            "read_holding_registers",
            "Modbus error",
            address=address,
            error=modbus_error,
        )
        raise SinapsiModbusError(
            f"Modbus operation failed: {modbus_error}",
            address=address,
            operation="read_holding_registers",
        ) from modbus_error
```

#### 2.7 Update Decode Method

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 404-416 (`_decode_register_value` method)

```python
def _decode_register_value(self, registers: list[int], reg_type: str) -> float:
    """Decode register value based on type.

    ModbusLink returns List[int] (16-bit unsigned values).
    We need to combine them for 32-bit values (big endian).
    """
    if reg_type == "uint16":
        return round(float(registers[0]), 2)
    elif reg_type == "uint32":
        # Big endian: high word first, then low word
        value = (registers[0] << 16) | registers[1]
        return round(float(value), 2)
    else:
        raise ValueError(f"Unsupported register type: {reg_type}")
```

#### 2.8 Update Sensor Read Method

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 464-485 (`_read_and_process_sensor` method)

```python
async def _read_and_process_sensor(self, sensor: dict[str, Any]) -> None:
    """Read and process a single sensor."""
    reg_key = sensor["key"]
    reg_addr = sensor["modbus_addr"]
    reg_type = sensor["modbus_type"]
    reg_count = 1 if reg_type == "uint16" else 2

    log_debug(
        _LOGGER, "_read_and_process_sensor", f"Reading {reg_key}", address=reg_addr
    )

    # ModbusLink returns List[int] directly
    registers = await self.read_holding_registers(reg_addr, reg_count)
    raw_value = self._decode_register_value(registers, reg_type)
    processed_value = self._process_sensor_value(raw_value, sensor)

    self.data[reg_key] = processed_value
    log_debug(
        _LOGGER,
        "_read_and_process_sensor",
        f"Processed {reg_key}",
        value=processed_value,
    )
```

#### 2.9 Update Exception Handling in async_get_data

**File**: `custom_components/sinapsi_alfa/api.py`
**Lines**: 524-544

```python
# CHANGE
except ConnectionException as connect_error:

# TO
except (ModbusConnectionError, ModbusTimeoutError) as connect_error:
```

### Phase 3: Cleanup

#### 3.1 Delete Deprecated Files

```bash
rm custom_components/sinapsi_alfa/pymodbus_constants.py
rm custom_components/sinapsi_alfa/pymodbus_payload.py
```

#### 3.2 Update CLAUDE.md

Remove references to `pymodbus_constants.py` and `pymodbus_payload.py` from documentation.

### Phase 4: Testing Checklist

- [ ] All 24 sensors read correctly (20 device + 4 calculated)
- [ ] uint16 registers decode correctly
- [ ] uint32 registers decode correctly (big endian)
- [ ] Connection/disconnection cycles work
- [ ] Device offline scenarios handled
- [ ] Timeout scenarios handled
- [ ] Integration reload works
- [ ] Integration unload works
- [ ] Long-running stability (24+ hours)
- [ ] No memory leaks
- [ ] Error messages are clear and actionable

______________________________________________________________________

## Risk Assessment & Mitigation

| Risk                   | Severity | Likelihood | Mitigation                       |
| ---------------------- | -------- | ---------- | -------------------------------- |
| Library bugs           | HIGH     | MEDIUM     | Extensive testing, rollback plan |
| API changes            | MEDIUM   | LOW        | Pin version `>=1.2.0,<2.0.0`     |
| Maintainer abandonment | MEDIUM   | LOW        | Keep pymodbus branch ready       |
| HA compatibility       | LOW      | LOW        | Test with HA betas               |
| Performance regression | LOW      | LOW        | Benchmark before/after           |

______________________________________________________________________

## Rollback Strategy

If critical issues arise:

1. **Immediate**: Revert to previous release tag
1. **Short-term**: Maintain `pymodbus-backup` branch
1. **Long-term**: Keep pymodbus migration path documented

### Rollback Commands

```bash
# Revert to last pymodbus version
git checkout v0.5.0
git checkout -b hotfix/revert-modbuslink
git push origin hotfix/revert-modbuslink

# Create emergency release
git tag -a v0.5.1 -m "Revert ModbusLink migration"
git push --tags
```

______________________________________________________________________

## Implementation Timeline

| Phase     | Description                         | Estimated Effort |
| --------- | ----------------------------------- | ---------------- |
| 1         | Preparation (branch, dependencies)  | Minimal          |
| 2         | API refactoring                     | 2-3 hours        |
| 3         | Cleanup (delete files, update docs) | 30 minutes       |
| 4         | Testing                             | 2-4 hours        |
| **Total** |                                     | **5-8 hours**    |

______________________________________________________________________

## References

- [ModbusLink GitHub](https://github.com/Miraitowa-la/ModbusLink)
- [ModbusLink Documentation](https://miraitowa-la.github.io/ModbusLink/en/index.html)
- [ModbusLink PyPI](https://pypi.org/project/modbuslink/)
- [pymodbus Documentation](https://pymodbus.readthedocs.io/)
- [pymodbus PyPI](https://pypi.org/project/pymodbus/)

______________________________________________________________________

## Document History

| Date       | Version | Changes                   |
| ---------- | ------- | ------------------------- |
| 2025-12-06 | 1.0     | Initial analysis document |
