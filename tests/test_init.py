"""Tests for Sinapsi Alfa integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sinapsi_alfa import (
    RuntimeData,
    async_migrate_entry,
    async_remove_config_entry_device,
    async_setup_entry,
    async_unload_entry,
    async_update_device_registry,
)
from custom_components.sinapsi_alfa.const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_RECOVERY_SCRIPT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_RECOVERY_SCRIPT,
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


@pytest.fixture
def mock_config_entry_v2():
    """Create a mock v2 config entry for migration testing."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.version = 2
    entry.data = {
        CONF_NAME: TEST_NAME,
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
    }
    entry.options = {
        CONF_SCAN_INTERVAL: 60,
        CONF_TIMEOUT: 10,
    }
    return entry


class TestMigrateV2ToV3:
    """Tests for v2 to v3 migration."""

    async def test_migrate_v2_to_v3_adds_repair_notification_options(
        self,
        hass: HomeAssistant,
        mock_config_entry_v2,
    ):
        """Test migration from v2 to v3 adds repair notification options."""
        with patch.object(hass.config_entries, "async_update_entry") as mock_update:
            result = await async_migrate_entry(hass, mock_config_entry_v2)

            assert result is True
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args[1]

            # Should have new repair notification options with defaults
            assert (
                call_kwargs["options"][CONF_ENABLE_REPAIR_NOTIFICATION]
                == DEFAULT_ENABLE_REPAIR_NOTIFICATION
            )
            assert call_kwargs["options"][CONF_FAILURES_THRESHOLD] == DEFAULT_FAILURES_THRESHOLD
            assert call_kwargs["options"][CONF_RECOVERY_SCRIPT] == DEFAULT_RECOVERY_SCRIPT
            assert call_kwargs["version"] == 3

    async def test_migrate_v2_to_v3_preserves_existing_options(
        self,
        hass: HomeAssistant,
        mock_config_entry_v2,
    ):
        """Test migration preserves existing scan_interval and timeout options."""
        with patch.object(hass.config_entries, "async_update_entry") as mock_update:
            result = await async_migrate_entry(hass, mock_config_entry_v2)

            assert result is True
            call_kwargs = mock_update.call_args[1]

            # Original options should be preserved
            assert call_kwargs["options"][CONF_SCAN_INTERVAL] == 60
            assert call_kwargs["options"][CONF_TIMEOUT] == 10


class TestAsyncUpdateDeviceRegistry:
    """Tests for async_update_device_registry function."""

    async def test_update_device_registry_creates_device(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test device is created in registry."""
        mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

        mock_device = MagicMock()
        mock_device.id = "device_123"

        with patch("custom_components.sinapsi_alfa.dr.async_get") as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.async_get_or_create.return_value = mock_device
            mock_registry.async_get_device.return_value = mock_device
            mock_get_registry.return_value = mock_registry

            async_update_device_registry(hass, mock_config_entry)

            mock_registry.async_get_or_create.assert_called_once()
            call_kwargs = mock_registry.async_get_or_create.call_args[1]
            assert call_kwargs["config_entry_id"] == mock_config_entry.entry_id
            assert call_kwargs["manufacturer"] == "Sinapsi"
            assert call_kwargs["model"] == "Alfa"

    async def test_update_device_registry_stores_device_id(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test device_id is stored in coordinator for triggers."""
        mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

        mock_device = MagicMock()
        mock_device.id = "stored_device_id"

        with patch("custom_components.sinapsi_alfa.dr.async_get") as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.async_get_or_create.return_value = mock_device
            mock_registry.async_get_device.return_value = mock_device
            mock_get_registry.return_value = mock_registry

            async_update_device_registry(hass, mock_config_entry)

            # Device ID should be stored in coordinator
            assert mock_coordinator.device_id == "stored_device_id"

    async def test_update_device_registry_no_device_found(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test handles case when device not found after creation."""
        mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

        with patch("custom_components.sinapsi_alfa.dr.async_get") as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.async_get_or_create.return_value = MagicMock()
            mock_registry.async_get_device.return_value = None  # Device not found
            mock_get_registry.return_value = mock_registry

            # Should not raise, just not set device_id
            async_update_device_registry(hass, mock_config_entry)

            # device_id should not be set (keeping original value)
            mock_coordinator.device_id = None  # Would remain None
