"""Tests for Sinapsi Alfa diagnostics module.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sinapsi_alfa.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SKIP_MAC_DETECTION,
    CONF_TIMEOUT,
    DOMAIN,
    VERSION,
)
from custom_components.sinapsi_alfa.diagnostics import async_get_config_entry_diagnostics
from homeassistant.core import HomeAssistant

from .conftest import TEST_HOST, TEST_MAC, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_TIMEOUT


@pytest.fixture
def mock_coordinator(mock_api_data):
    """Create a mock coordinator with API data."""
    coordinator = MagicMock()
    coordinator.api = MagicMock()
    coordinator.api.data = mock_api_data
    coordinator.api.data["sn"] = TEST_MAC
    coordinator.api.data["manufact"] = "Sinapsi"
    coordinator.api.data["model"] = "Alfa"
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(seconds=60)
    return coordinator


class TestDiagnostics:
    """Tests for diagnostics functionality."""

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics returns expected structure."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_TIMEOUT: TEST_TIMEOUT,
            },
        )
        entry.add_to_hass(hass)

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        # Check structure
        assert "config" in result
        assert "device" in result
        assert "coordinator" in result
        assert "sensors" in result

    @pytest.mark.asyncio
    async def test_diagnostics_config_section(self, hass: HomeAssistant, mock_coordinator) -> None:
        """Test diagnostics config section content."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_TIMEOUT: TEST_TIMEOUT,
            },
        )
        entry.add_to_hass(hass)

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        config = result["config"]
        assert config["entry_id"] == entry.entry_id
        assert config["version"] == entry.version
        assert config["domain"] == DOMAIN
        assert config["integration_version"] == VERSION
        assert config["options"][CONF_SCAN_INTERVAL] == TEST_SCAN_INTERVAL
        assert config["options"][CONF_TIMEOUT] == TEST_TIMEOUT

    @pytest.mark.asyncio
    async def test_diagnostics_device_section(self, hass: HomeAssistant, mock_coordinator) -> None:
        """Test diagnostics device section content."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_TIMEOUT: TEST_TIMEOUT,
            },
        )
        entry.add_to_hass(hass)

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        device = result["device"]
        assert device["name"] == TEST_NAME
        assert device["port"] == TEST_PORT
        assert device["manufacturer"] == "Sinapsi"
        assert device["model"] == "Alfa"
        # Serial number should be redacted
        assert device["serial_number"] == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_diagnostics_coordinator_section(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics coordinator section content."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_TIMEOUT: TEST_TIMEOUT,
            },
        )
        entry.add_to_hass(hass)

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        coordinator = result["coordinator"]
        assert coordinator["last_update_success"] is True
        assert coordinator["update_interval_seconds"] == 60.0

    @pytest.mark.asyncio
    async def test_diagnostics_redacts_sensitive_data(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics redacts sensitive data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_TIMEOUT: TEST_TIMEOUT,
            },
        )
        entry.add_to_hass(hass)

        # Add sensitive data to API data
        mock_coordinator.api.data["sn"] = "SENSITIVE123"
        mock_coordinator.api.data["host"] = "192.168.1.100"

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        sensors = result["sensors"]
        # Serial number should be redacted
        assert sensors["sn"] == "**REDACTED**"
        # Host should be redacted if in data
        if "host" in sensors:
            assert sensors["host"] == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_diagnostics_includes_sensor_data(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics includes sensor data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_TIMEOUT: TEST_TIMEOUT,
            },
        )
        entry.add_to_hass(hass)

        # Set some sensor values
        mock_coordinator.api.data["potenza_prodotta"] = 2.5
        mock_coordinator.api.data["potenza_consumata"] = 1.8

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        sensors = result["sensors"]
        assert sensors["potenza_prodotta"] == 2.5
        assert sensors["potenza_consumata"] == 1.8

    @pytest.mark.asyncio
    async def test_diagnostics_config_data_redacted(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics redacts host from config data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_TIMEOUT: TEST_TIMEOUT,
            },
        )
        entry.add_to_hass(hass)

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        config_data = result["config"]["data"]
        # Host should be redacted
        assert config_data.get(CONF_HOST) == "**REDACTED**"
        # Name should NOT be redacted
        assert config_data.get(CONF_NAME) == TEST_NAME

    @pytest.mark.asyncio
    async def test_diagnostics_with_no_update_interval(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics handles None update_interval."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_TIMEOUT: TEST_TIMEOUT,
            },
        )
        entry.add_to_hass(hass)

        mock_coordinator.update_interval = None

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        coordinator = result["coordinator"]
        assert coordinator["update_interval_seconds"] is None
