"""Tests for Sinapsi Alfa integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sinapsi_alfa import (
    RuntimeData,
    async_migrate_entry,
    async_remove_config_entry_device,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.sinapsi_alfa.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .conftest import TEST_HOST, TEST_MAC, TEST_NAME, TEST_PORT


@pytest.fixture
def mock_coordinator():
    """Create mock coordinator."""
    coordinator = MagicMock()
    coordinator.api = MagicMock()
    coordinator.api.data = {
        "sn": TEST_MAC,
        "model": "Alfa",
        "manufact": "Sinapsi",
    }
    coordinator.api.name = TEST_NAME
    coordinator.api.host = TEST_HOST
    coordinator.api.close = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    return coordinator


@pytest.fixture
def mock_config_entry_v1():
    """Create a mock v1 config entry for migration testing."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.version = 1
    entry.data = {
        CONF_NAME: TEST_NAME,
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
        CONF_SCAN_INTERVAL: 120,
        CONF_TIMEOUT: 15,
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_config_entry_v1_no_optional():
    """Create a mock v1 config entry without optional fields."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.version = 1
    entry.data = {
        CONF_NAME: TEST_NAME,
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_config_entry_future():
    """Create a mock config entry from future version."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.version = 99
    entry.data = {}
    entry.options = {}
    return entry


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    async def test_setup_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test successful setup."""
        with (
            patch(
                "custom_components.sinapsi_alfa.SinapsiAlfaCoordinator",
                return_value=mock_coordinator,
            ),
            patch(
                "custom_components.sinapsi_alfa.async_update_device_registry",
            ) as mock_device_reg,
            patch.object(hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock),
        ):
            result = await async_setup_entry(hass, mock_config_entry)

            assert result is True
            assert mock_config_entry.runtime_data is not None
            assert isinstance(mock_config_entry.runtime_data, RuntimeData)
            mock_device_reg.assert_called_once()

    async def test_setup_entry_no_serial_raises_not_ready(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test setup raises ConfigEntryNotReady when no serial number."""
        mock_coordinator.api.data["sn"] = ""  # Empty serial

        with (
            patch(
                "custom_components.sinapsi_alfa.SinapsiAlfaCoordinator",
                return_value=mock_coordinator,
            ),
            pytest.raises(ConfigEntryNotReady),
        ):
            await async_setup_entry(hass, mock_config_entry)


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    async def test_unload_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test successful unload."""
        mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await async_unload_entry(hass, mock_config_entry)

            assert result is True
            mock_coordinator.api.close.assert_called_once()

    async def test_unload_entry_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test unload failure does not cleanup."""
        mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await async_unload_entry(hass, mock_config_entry)

            assert result is False
            mock_coordinator.api.close.assert_not_called()


class TestAsyncMigrateEntry:
    """Tests for async_migrate_entry."""

    async def test_migrate_v1_to_v2_with_optional_fields(
        self,
        hass: HomeAssistant,
        mock_config_entry_v1,
    ):
        """Test migration from v1 to v2 with optional fields present."""
        with patch.object(hass.config_entries, "async_update_entry") as mock_update:
            result = await async_migrate_entry(hass, mock_config_entry_v1)

            assert result is True
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args[1]
            # scan_interval and timeout should be in options now
            assert CONF_SCAN_INTERVAL in call_kwargs["options"]
            assert CONF_TIMEOUT in call_kwargs["options"]
            assert call_kwargs["options"][CONF_SCAN_INTERVAL] == 120
            assert call_kwargs["options"][CONF_TIMEOUT] == 15
            # Should not be in data anymore
            assert CONF_SCAN_INTERVAL not in call_kwargs["data"]
            assert CONF_TIMEOUT not in call_kwargs["data"]
            assert call_kwargs["version"] == 2

    async def test_migrate_v1_to_v2_without_optional_fields(
        self,
        hass: HomeAssistant,
        mock_config_entry_v1_no_optional,
    ):
        """Test migration from v1 to v2 without optional fields uses defaults."""
        with patch.object(hass.config_entries, "async_update_entry") as mock_update:
            result = await async_migrate_entry(hass, mock_config_entry_v1_no_optional)

            assert result is True
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args[1]
            # Should have default values
            assert call_kwargs["options"][CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
            assert call_kwargs["options"][CONF_TIMEOUT] == DEFAULT_TIMEOUT

    async def test_migrate_from_future_version_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry_future,
    ):
        """Test migration from future version fails gracefully."""
        result = await async_migrate_entry(hass, mock_config_entry_future)
        assert result is False


class TestAsyncRemoveConfigEntryDevice:
    """Tests for async_remove_config_entry_device."""

    async def test_remove_device_with_domain_identifier(self, hass: HomeAssistant):
        """Test cannot remove device with domain identifier."""
        config_entry = MagicMock()
        device_entry = MagicMock()
        device_entry.identifiers = {(DOMAIN, TEST_MAC)}

        result = await async_remove_config_entry_device(hass, config_entry, device_entry)
        assert result is False

    async def test_remove_device_without_domain_identifier(self, hass: HomeAssistant):
        """Test can remove device without domain identifier."""
        config_entry = MagicMock()
        device_entry = MagicMock()
        device_entry.identifiers = {("other_domain", "some_id")}

        result = await async_remove_config_entry_device(hass, config_entry, device_entry)
        assert result is True


class TestRuntimeData:
    """Tests for RuntimeData dataclass."""

    def test_runtime_data_creation(self, mock_coordinator):
        """Test RuntimeData can be created."""
        runtime_data = RuntimeData(coordinator=mock_coordinator)
        assert runtime_data.coordinator is mock_coordinator
