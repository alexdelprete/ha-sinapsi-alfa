"""Tests for Sinapsi Alfa helper functions."""

import logging
import socket
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.sinapsi_alfa.helpers import (
    check_modbus_conflict,
    host_valid,
    log_debug,
    log_error,
    log_info,
    log_warning,
    resolve_host_to_ip,
    unix_timestamp_to_iso8601_local_tz,
)


class TestHostValid:
    """Tests for host_valid function."""

    def test_valid_ipv4(self):
        """Test valid IPv4 addresses."""
        assert host_valid("192.168.1.1") is True
        assert host_valid("10.0.0.1") is True
        assert host_valid("172.16.0.1") is True
        assert host_valid("0.0.0.0") is True
        assert host_valid("255.255.255.255") is True

    def test_valid_ipv6(self):
        """Test valid IPv6 addresses."""
        assert host_valid("::1") is True
        assert host_valid("fe80::1") is True
        assert host_valid("2001:db8::1") is True

    def test_valid_hostname(self):
        """Test valid hostnames."""
        assert host_valid("localhost") is True
        assert host_valid("my-device") is True
        assert host_valid("alfa.local") is True
        assert host_valid("device-1.home.lan") is True

    def test_invalid_hostname_special_chars(self):
        """Test invalid hostnames with special characters."""
        assert host_valid("device@home") is False
        assert host_valid("device#1") is False
        assert host_valid("my_device") is False  # underscores not allowed
        assert host_valid("device!") is False

    def test_invalid_hostname_empty_parts(self):
        """Test invalid hostnames with empty parts."""
        assert host_valid(".local") is False
        assert host_valid("device.") is False
        assert host_valid("..") is False

    def test_invalid_ip(self):
        """Test invalid IP addresses and hostnames."""
        # 256.1.1.1 fails IP validation but passes hostname validation (digits/dots allowed)
        assert host_valid("256.1.1.1") is True  # Valid as hostname, invalid as IP
        # These fail both IP and hostname validation
        assert host_valid("not-a-valid-host!!!") is False


class TestUnixTimestampToIso8601:
    """Tests for unix_timestamp_to_iso8601_local_tz function."""

    def test_valid_timestamp(self):
        """Test valid timestamp conversion."""
        # Just verify it returns a valid ISO8601 string
        result = unix_timestamp_to_iso8601_local_tz(1739238065)
        assert isinstance(result, str)
        # ISO8601 format: YYYY-MM-DDTHH:MM:SS+HH:MM
        assert "T" in result
        assert "2025" in result  # The year from the timestamp

    def test_zero_timestamp(self):
        """Test epoch timestamp."""
        result = unix_timestamp_to_iso8601_local_tz(0)
        assert isinstance(result, str)
        assert "1970" in result

    def test_recent_timestamp(self):
        """Test a recent timestamp."""
        result = unix_timestamp_to_iso8601_local_tz(1704067200)  # 2024-01-01 00:00:00 UTC
        assert isinstance(result, str)
        assert "2024" in result


class TestResolveHostToIp:
    """Tests for resolve_host_to_ip function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock()
        return hass

    @pytest.mark.asyncio
    async def test_resolve_ip_address_returns_same(self, mock_hass):
        """Test that an IP address is returned as-is without resolution."""
        result = await resolve_host_to_ip(mock_hass, "192.168.1.100")
        assert result == "192.168.1.100"
        # Should not call executor job for IP addresses
        mock_hass.async_add_executor_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_ipv6_address_returns_same(self, mock_hass):
        """Test that an IPv6 address is returned as-is."""
        result = await resolve_host_to_ip(mock_hass, "::1")
        assert result == "::1"
        mock_hass.async_add_executor_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_hostname_success(self, mock_hass):
        """Test successful hostname resolution."""
        mock_hass.async_add_executor_job.return_value = "192.168.1.50"

        result = await resolve_host_to_ip(mock_hass, "alfa.local")

        assert result == "192.168.1.50"
        mock_hass.async_add_executor_job.assert_called_once_with(socket.gethostbyname, "alfa.local")

    @pytest.mark.asyncio
    async def test_resolve_hostname_failure(self, mock_hass):
        """Test hostname resolution failure returns None."""
        mock_hass.async_add_executor_job.side_effect = socket.gaierror("Name resolution failed")

        result = await resolve_host_to_ip(mock_hass, "nonexistent.host")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_fqdn_success(self, mock_hass):
        """Test FQDN resolution."""
        mock_hass.async_add_executor_job.return_value = "10.0.0.5"

        result = await resolve_host_to_ip(mock_hass, "device.home.lan")

        assert result == "10.0.0.5"


class TestCheckModbusConflict:
    """Tests for check_modbus_conflict function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock()
        hass.config_entries = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_no_modbus_entries_no_conflict(self, mock_hass):
        """Test no conflict when no Modbus entries exist."""
        mock_hass.config_entries.async_entries.return_value = []

        result = await check_modbus_conflict(mock_hass, "192.168.1.100")

        assert result is None
        mock_hass.config_entries.async_entries.assert_called_once_with(domain="modbus")

    @pytest.mark.asyncio
    async def test_modbus_entry_different_host_no_conflict(self, mock_hass):
        """Test no conflict when Modbus entry has different host."""
        modbus_entry = MagicMock()
        modbus_entry.data = {"host": "192.168.1.200"}
        mock_hass.config_entries.async_entries.return_value = [modbus_entry]
        # Both are IP addresses, no resolution needed for our host
        # For modbus host, we need to resolve it
        mock_hass.async_add_executor_job.return_value = "192.168.1.200"

        result = await check_modbus_conflict(mock_hass, "192.168.1.100")

        assert result is None

    @pytest.mark.asyncio
    async def test_modbus_entry_same_ip_conflict(self, mock_hass):
        """Test conflict detected when Modbus entry has same IP."""
        modbus_entry = MagicMock()
        modbus_entry.data = {"host": "192.168.1.100"}
        mock_hass.config_entries.async_entries.return_value = [modbus_entry]

        result = await check_modbus_conflict(mock_hass, "192.168.1.100")

        assert result == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_modbus_entry_hostname_resolves_to_same_ip(self, mock_hass):
        """Test conflict when hostname resolves to same IP."""
        modbus_entry = MagicMock()
        modbus_entry.data = {"host": "alfa.local"}
        mock_hass.config_entries.async_entries.return_value = [modbus_entry]
        # Mock hostname resolution to same IP
        mock_hass.async_add_executor_job.return_value = "192.168.1.100"

        result = await check_modbus_conflict(mock_hass, "192.168.1.100")

        assert result == "alfa.local"

    @pytest.mark.asyncio
    async def test_our_hostname_resolves_to_modbus_ip(self, mock_hass):
        """Test conflict when our hostname resolves to Modbus IP."""
        modbus_entry = MagicMock()
        modbus_entry.data = {"host": "192.168.1.100"}
        mock_hass.config_entries.async_entries.return_value = [modbus_entry]
        # Our hostname resolves to the Modbus IP
        mock_hass.async_add_executor_job.return_value = "192.168.1.100"

        result = await check_modbus_conflict(mock_hass, "alfa.local")

        assert result == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_modbus_entry_without_host_no_conflict(self, mock_hass):
        """Test no conflict when Modbus entry has no host."""
        modbus_entry = MagicMock()
        modbus_entry.data = {}  # No host key
        mock_hass.config_entries.async_entries.return_value = [modbus_entry]

        result = await check_modbus_conflict(mock_hass, "192.168.1.100")

        assert result is None

    @pytest.mark.asyncio
    async def test_modbus_host_resolution_fails_no_conflict(self, mock_hass):
        """Test no conflict when Modbus hostname cannot be resolved."""
        modbus_entry = MagicMock()
        modbus_entry.data = {"host": "unknown.host"}
        mock_hass.config_entries.async_entries.return_value = [modbus_entry]
        # Modbus host resolution fails
        mock_hass.async_add_executor_job.side_effect = socket.gaierror("Resolution failed")

        result = await check_modbus_conflict(mock_hass, "192.168.1.100")

        assert result is None

    @pytest.mark.asyncio
    async def test_our_host_resolution_fails_no_conflict(self, mock_hass):
        """Test no conflict when our hostname cannot be resolved."""
        modbus_entry = MagicMock()
        modbus_entry.data = {"host": "192.168.1.100"}
        mock_hass.config_entries.async_entries.return_value = [modbus_entry]
        # Our host resolution fails
        mock_hass.async_add_executor_job.side_effect = socket.gaierror("Resolution failed")

        result = await check_modbus_conflict(mock_hass, "unknown.host")

        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_modbus_entries_finds_conflict(self, mock_hass):
        """Test conflict found among multiple Modbus entries."""
        modbus_entry1 = MagicMock()
        modbus_entry1.data = {"host": "192.168.1.50"}
        modbus_entry2 = MagicMock()
        modbus_entry2.data = {"host": "192.168.1.100"}  # This conflicts
        modbus_entry3 = MagicMock()
        modbus_entry3.data = {"host": "192.168.1.200"}
        mock_hass.config_entries.async_entries.return_value = [
            modbus_entry1,
            modbus_entry2,
            modbus_entry3,
        ]

        result = await check_modbus_conflict(mock_hass, "192.168.1.100")

        assert result == "192.168.1.100"


class TestLoggingHelpers:
    """Tests for logging helper functions."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock(spec=logging.Logger)

    def test_log_debug_simple(self, mock_logger):
        """Test log_debug without kwargs."""
        log_debug(mock_logger, "test_context", "Test message")
        mock_logger.debug.assert_called_once_with("%s: %s", "(test_context)", "Test message")

    def test_log_debug_with_kwargs(self, mock_logger):
        """Test log_debug with kwargs."""
        log_debug(mock_logger, "test_context", "Test message", key1="value1", key2="value2")
        call_args = mock_logger.debug.call_args
        assert "(test_context)" in call_args[0][1]
        assert "key1=value1" in call_args[0][1]
        assert "key2=value2" in call_args[0][1]

    def test_log_info_simple(self, mock_logger):
        """Test log_info without kwargs."""
        log_info(mock_logger, "test_context", "Test message")
        mock_logger.info.assert_called_once_with("%s: %s", "(test_context)", "Test message")

    def test_log_info_with_kwargs(self, mock_logger):
        """Test log_info with kwargs."""
        log_info(mock_logger, "test_context", "Test message", value=42)
        call_args = mock_logger.info.call_args
        assert "(test_context)" in call_args[0][1]
        assert "value=42" in call_args[0][1]

    def test_log_warning_simple(self, mock_logger):
        """Test log_warning without kwargs."""
        log_warning(mock_logger, "test_context", "Test message")
        mock_logger.warning.assert_called_once_with("%s: %s", "(test_context)", "Test message")

    def test_log_warning_with_kwargs(self, mock_logger):
        """Test log_warning with kwargs."""
        log_warning(mock_logger, "test_context", "Test message", error="something")
        call_args = mock_logger.warning.call_args
        assert "(test_context)" in call_args[0][1]
        assert "error=something" in call_args[0][1]

    def test_log_error_simple(self, mock_logger):
        """Test log_error without kwargs."""
        log_error(mock_logger, "test_context", "Test message")
        mock_logger.error.assert_called_once_with("%s: %s", "(test_context)", "Test message")

    def test_log_error_with_kwargs(self, mock_logger):
        """Test log_error with kwargs."""
        log_error(mock_logger, "test_context", "Test message", code=500)
        call_args = mock_logger.error.call_args
        assert "(test_context)" in call_args[0][1]
        assert "code=500" in call_args[0][1]
