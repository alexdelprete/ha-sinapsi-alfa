"""Common fixtures for Sinapsi Alfa tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sinapsi_alfa.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SKIP_MAC_DETECTION,
    CONF_TIMEOUT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant

# Test configuration values
TEST_HOST = "192.168.1.100"
TEST_NAME = "Test Alfa"
TEST_PORT = DEFAULT_PORT
TEST_SCAN_INTERVAL = DEFAULT_SCAN_INTERVAL
TEST_TIMEOUT = DEFAULT_TIMEOUT
TEST_MAC = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Return mock config entry data."""
    return {
        CONF_NAME: TEST_NAME,
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
        CONF_SKIP_MAC_DETECTION: False,
    }


@pytest.fixture
def mock_config_entry_options() -> dict:
    """Return mock config entry options."""
    return {
        CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
        CONF_TIMEOUT: TEST_TIMEOUT,
    }


@pytest.fixture
def mock_api_data() -> dict:
    """Return mock data from SinapsiAlfaAPI."""
    return {
        "manufact": "Sinapsi",
        "model": "Alfa",
        "sn": TEST_MAC,
        "potenza_prelevata": 1.5,
        "potenza_immessa": 0.0,
        "potenza_prodotta": 2.0,
        "potenza_prelevata_media_15m": 1.4,
        "potenza_immessa_media_15m": 0.1,
        "energia_prelevata": 12345.6,
        "energia_immessa": 1234.5,
        "energia_prodotta": 5678.9,
        "energia_prelevata_giornaliera_f1": 10.0,
        "energia_prelevata_giornaliera_f2": 5.0,
        "energia_prelevata_giornaliera_f3": 3.0,
        "energia_prelevata_giornaliera_f4": 0.0,
        "energia_prelevata_giornaliera_f5": 0.0,
        "energia_prelevata_giornaliera_f6": 0.0,
        "energia_immessa_giornaliera_f1": 2.0,
        "energia_immessa_giornaliera_f2": 1.0,
        "energia_immessa_giornaliera_f3": 0.5,
        "energia_immessa_giornaliera_f4": 0.0,
        "energia_immessa_giornaliera_f5": 0.0,
        "energia_immessa_giornaliera_f6": 0.0,
        "fascia_oraria_attuale": "F1",
        "tempo_residuo_distacco": None,
        "data_evento": None,
        "potenza_consumata": 3.5,
        "potenza_auto_consumata": 2.0,
        "energia_consumata": 16790.0,
        "energia_auto_consumata": 4444.4,
    }


@pytest.fixture
def mock_sinapsi_api(mock_api_data: dict) -> Generator[MagicMock]:
    """Mock SinapsiAlfaAPI."""
    with patch(
        "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.data = mock_api_data
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)
        mock_api.close = AsyncMock()
        yield mock_api


@pytest.fixture
def mock_sinapsi_api_coordinator(mock_api_data: dict) -> Generator[MagicMock]:
    """Mock SinapsiAlfaAPI for coordinator tests."""
    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.data = mock_api_data
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)
        mock_api.close = AsyncMock()
        yield mock_api


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.sinapsi_alfa.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations in Home Assistant."""


@pytest.fixture
def mock_config_entry(
    hass: HomeAssistant,
    mock_config_entry_data: dict,
    mock_config_entry_options: dict,
) -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = mock_config_entry_data
    entry.options = mock_config_entry_options
    entry.unique_id = TEST_MAC
    entry.title = TEST_NAME
    entry.version = 2
    return entry


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock HomeAssistant instance for direct unit tests.

    This fixture is used for tests that don't require full HA integration loading.
    It provides a minimal mock that can be used to test coordinator and other
    component logic directly without needing the real HA event bus/services.

    Note: For integration tests, use the built-in `hass` fixture from
    pytest_homeassistant_custom_component instead.
    """
    mock = MagicMock(spec=HomeAssistant)
    mock.config_entries = MagicMock()
    mock.config_entries.async_entries = MagicMock(return_value=[])
    mock.data = {}  # Required for enable_custom_integrations fixture

    # Add state for coordinator base class checks
    mock.state = CoreState.running

    # Add loop for async operations (required by DataUpdateCoordinator)
    mock.loop = asyncio.get_event_loop()

    # Add bus for event firing
    mock.bus = MagicMock()
    mock.bus.async_fire = MagicMock()

    # Add config for recovery script path resolution
    mock.config = MagicMock()
    mock.config.is_allowed_path = MagicMock(return_value=True)

    # Add services for script execution
    mock.services = MagicMock()
    mock.services.async_call = AsyncMock()

    return mock
