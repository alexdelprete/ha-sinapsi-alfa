"""Tests for Sinapsi Alfa helper functions."""

import logging
from unittest.mock import MagicMock

import pytest

from custom_components.sinapsi_alfa.helpers import (
    host_valid,
    log_debug,
    log_error,
    log_info,
    log_warning,
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
        """Test invalid IP addresses (caught as hostnames)."""
        # These fail IP validation, then hostname validation
        assert host_valid("256.1.1.1") is False  # invalid IP, invalid hostname (digits only)
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
