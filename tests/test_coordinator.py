"""Tests for Sinapsi Alfa coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sinapsi_alfa.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SKIP_MAC_DETECTION,
    CONF_TIMEOUT,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MAX_TIMEOUT,
    MIN_SCAN_INTERVAL,
    MIN_TIMEOUT,
)
from custom_components.sinapsi_alfa.coordinator import SinapsiAlfaCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import TEST_HOST, TEST_MAC, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_TIMEOUT


def create_mock_config_entry(
    scan_interval: int = TEST_SCAN_INTERVAL,
    timeout: int = TEST_TIMEOUT,
    skip_mac_detection: bool = False,
) -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.unique_id = TEST_MAC
    entry.title = TEST_NAME
    entry.data = {
        CONF_NAME: TEST_NAME,
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
        CONF_SKIP_MAC_DETECTION: skip_mac_detection,
    }
    entry.options = {
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_TIMEOUT: timeout,
    }
    return entry


async def test_coordinator_init(
    hass: HomeAssistant,
    mock_sinapsi_api_coordinator,
) -> None:
    """Test coordinator initialization."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ):
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator.conf_name == TEST_NAME
        assert coordinator.conf_host == TEST_HOST
        assert coordinator.conf_port == TEST_PORT
        assert coordinator.scan_interval == TEST_SCAN_INTERVAL
        assert coordinator.timeout == TEST_TIMEOUT
        assert coordinator.update_interval == timedelta(seconds=TEST_SCAN_INTERVAL)


async def test_coordinator_scan_interval_min_enforcement(
    hass: HomeAssistant,
) -> None:
    """Test coordinator enforces minimum scan interval."""
    entry = create_mock_config_entry(scan_interval=10)  # Below minimum

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ):
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator.scan_interval == MIN_SCAN_INTERVAL


async def test_coordinator_scan_interval_max_enforcement(
    hass: HomeAssistant,
) -> None:
    """Test coordinator enforces maximum scan interval."""
    entry = create_mock_config_entry(scan_interval=1000)  # Above maximum

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ):
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator.scan_interval == MAX_SCAN_INTERVAL


async def test_coordinator_timeout_min_enforcement(
    hass: HomeAssistant,
) -> None:
    """Test coordinator enforces minimum timeout."""
    entry = create_mock_config_entry(timeout=1)  # Below minimum

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ):
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator.timeout == MIN_TIMEOUT


async def test_coordinator_timeout_max_enforcement(
    hass: HomeAssistant,
) -> None:
    """Test coordinator enforces maximum timeout."""
    entry = create_mock_config_entry(timeout=120)  # Above maximum

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ):
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator.timeout == MAX_TIMEOUT


async def test_coordinator_update_success(
    hass: HomeAssistant,
    mock_api_data: dict,
) -> None:
    """Test successful data update."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        result = await coordinator.async_update_data()

        assert result == mock_api_data
        assert coordinator.last_update_status == mock_api_data
        mock_api.async_get_data.assert_called_once()


async def test_coordinator_update_failure(
    hass: HomeAssistant,
) -> None:
    """Test data update failure raises UpdateFailed."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        coordinator = SinapsiAlfaCoordinator(hass, entry)

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        assert coordinator.last_update_status is False


async def test_coordinator_skip_mac_detection(
    hass: HomeAssistant,
) -> None:
    """Test coordinator passes skip_mac_detection to API."""
    entry = create_mock_config_entry(skip_mac_detection=True)

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator.skip_mac_detection is True
        # Verify API was called with skip_mac_detection=True
        mock_api_class.assert_called_once_with(
            hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
            TEST_SCAN_INTERVAL,
            TEST_TIMEOUT,
            True,  # skip_mac_detection
        )
