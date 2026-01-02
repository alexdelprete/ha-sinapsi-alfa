"""Tests for Sinapsi Alfa coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sinapsi_alfa.api import SinapsiConnectionError, SinapsiModbusError
from custom_components.sinapsi_alfa.const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_RECOVERY_SCRIPT,
    CONF_SCAN_INTERVAL,
    CONF_SKIP_MAC_DETECTION,
    CONF_TIMEOUT,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_RECOVERY_SCRIPT,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MAX_TIMEOUT,
    MIN_SCAN_INTERVAL,
    MIN_TIMEOUT,
)
from custom_components.sinapsi_alfa.coordinator import SinapsiAlfaCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import TEST_HOST, TEST_MAC, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_TIMEOUT


def create_mock_config_entry(
    scan_interval: int = TEST_SCAN_INTERVAL,
    timeout: int = TEST_TIMEOUT,
    skip_mac_detection: bool = False,
    enable_repair_notification: bool = DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    failures_threshold: int = DEFAULT_FAILURES_THRESHOLD,
    recovery_script: str = DEFAULT_RECOVERY_SCRIPT,
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
        CONF_ENABLE_REPAIR_NOTIFICATION: enable_repair_notification,
        CONF_FAILURES_THRESHOLD: failures_threshold,
        CONF_RECOVERY_SCRIPT: recovery_script,
    }
    return entry


async def test_coordinator_init(
    hass: HomeAssistant,
) -> None:
    """Test coordinator initialization."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
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
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection timeout"))

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


async def test_coordinator_update_resets_failure_counter(
    hass: HomeAssistant,
    mock_api_data: dict,
) -> None:
    """Test successful update resets consecutive failure counter."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        # Simulate previous failures
        coordinator._consecutive_failures = 2

        await coordinator.async_update_data()

        assert coordinator._consecutive_failures == 0


async def test_coordinator_update_increments_failure_counter(
    hass: HomeAssistant,
) -> None:
    """Test failed update increments consecutive failure counter."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        assert coordinator._consecutive_failures == 0

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        assert coordinator._consecutive_failures == 1


async def test_coordinator_creates_repair_issue_after_repeated_failures(
    hass: HomeAssistant,
) -> None:
    """Test repair issue is created after repeated failures."""
    entry = create_mock_config_entry()

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_connection_issue",
        ) as mock_create_issue,
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        # Set failures just below threshold (uses configurable _failures_threshold)
        coordinator._consecutive_failures = DEFAULT_FAILURES_THRESHOLD - 1

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        # Now at threshold, issue should be created
        assert coordinator._consecutive_failures == DEFAULT_FAILURES_THRESHOLD
        mock_create_issue.assert_called_once_with(
            hass,
            entry.entry_id,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
        )
        assert coordinator._repair_issue_created is True


async def test_coordinator_does_not_create_duplicate_repair_issue(
    hass: HomeAssistant,
) -> None:
    """Test repair issue is not created if already exists."""
    entry = create_mock_config_entry()

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_connection_issue",
        ) as mock_create_issue,
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        # Simulate issue already created
        coordinator._consecutive_failures = DEFAULT_FAILURES_THRESHOLD
        coordinator._repair_issue_created = True

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        # Should not create another issue
        mock_create_issue.assert_not_called()


async def test_coordinator_deletes_repair_issue_on_success(
    hass: HomeAssistant,
    mock_api_data: dict,
) -> None:
    """Test repair issue is deleted when connection is restored."""
    entry = create_mock_config_entry()

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.delete_connection_issue",
        ) as mock_delete_issue,
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_recovery_notification",
        ),
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        # Simulate repair issue was previously created
        coordinator._repair_issue_created = True
        coordinator._consecutive_failures = DEFAULT_FAILURES_THRESHOLD

        await coordinator.async_update_data()

        # Issue should be deleted on successful update
        mock_delete_issue.assert_called_once_with(hass, entry.entry_id)
        assert coordinator._repair_issue_created is False
        assert coordinator._consecutive_failures == 0


async def test_coordinator_does_not_delete_nonexistent_repair_issue(
    hass: HomeAssistant,
    mock_api_data: dict,
) -> None:
    """Test no deletion attempted if repair issue wasn't created."""
    entry = create_mock_config_entry()

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.delete_connection_issue",
        ) as mock_delete_issue,
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        # No repair issue was created
        coordinator._repair_issue_created = False

        await coordinator.async_update_data()

        # Should not attempt to delete
        mock_delete_issue.assert_not_called()


async def test_coordinator_failure_below_threshold_no_issue(
    hass: HomeAssistant,
) -> None:
    """Test no repair issue created when failures below threshold."""
    entry = create_mock_config_entry()

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_connection_issue",
        ) as mock_create_issue,
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        # Start at 0 failures
        assert coordinator._consecutive_failures == 0

        # Fail once - should not create issue yet
        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        assert coordinator._consecutive_failures == 1
        mock_create_issue.assert_not_called()
        assert coordinator._repair_issue_created is False


async def test_coordinator_recovery_with_script_info(
    hass: HomeAssistant,
    mock_api_data: dict,
) -> None:
    """Test recovery notification includes script execution info."""
    entry = create_mock_config_entry(recovery_script="script.test_recovery")

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.delete_connection_issue",
        ),
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_recovery_notification",
        ) as mock_create_notification,
        patch("custom_components.sinapsi_alfa.coordinator.time") as mock_time,
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)
        mock_api.data = {"sn": "", "mac": ""}
        mock_time.time.return_value = 1000.0

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        # Simulate repair issue was created with script executed
        coordinator._repair_issue_created = True
        coordinator._failure_start_time = 900.0  # 100 seconds ago
        coordinator._recovery_script_executed = True
        coordinator._script_executed_time = 950.0

        await coordinator.async_update_data()

        # Check recovery notification was created with script info
        mock_create_notification.assert_called_once()
        call_kwargs = mock_create_notification.call_args[1]
        assert call_kwargs["script_name"] == "script.test_recovery"
        assert coordinator._repair_issue_created is False
        assert coordinator._recovery_script_executed is False


async def test_coordinator_recovery_without_script(
    hass: HomeAssistant,
    mock_api_data: dict,
) -> None:
    """Test recovery notification without script execution."""
    entry = create_mock_config_entry()

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.delete_connection_issue",
        ),
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_recovery_notification",
        ) as mock_create_notification,
        patch("custom_components.sinapsi_alfa.coordinator.time") as mock_time,
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)
        mock_api.data = {"sn": "", "mac": ""}
        mock_time.time.return_value = 1000.0

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        coordinator._repair_issue_created = True
        coordinator._failure_start_time = 940.0  # 60 seconds ago
        coordinator._recovery_script_executed = False

        await coordinator.async_update_data()

        mock_create_notification.assert_called_once()
        call_kwargs = mock_create_notification.call_args[1]
        assert call_kwargs["script_name"] is None
        assert call_kwargs["script_executed_at"] is None


async def test_coordinator_error_type_sinapsi_modbus_error(
    hass: HomeAssistant,
) -> None:
    """Test error type is device_not_responding for SinapsiModbusError."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=SinapsiModbusError("Invalid response"))

        coordinator = SinapsiAlfaCoordinator(hass, entry)

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        assert coordinator._last_error_type == "device_not_responding"


async def test_coordinator_error_type_sinapsi_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test error type is device_unreachable for SinapsiConnectionError."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(
            side_effect=SinapsiConnectionError("Connection refused")
        )

        coordinator = SinapsiAlfaCoordinator(hass, entry)

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        assert coordinator._last_error_type == "device_unreachable"


async def test_coordinator_execute_recovery_script(
    mock_hass: MagicMock,
) -> None:
    """Test recovery script is executed after threshold failures."""
    entry = create_mock_config_entry(recovery_script="script.restart_device")

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_connection_issue",
        ),
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))
        mock_api.data = {"sn": "SN123", "mac": "AA:BB:CC:DD:EE:FF"}

        coordinator = SinapsiAlfaCoordinator(mock_hass, entry)
        coordinator._consecutive_failures = DEFAULT_FAILURES_THRESHOLD - 1

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        # Script should have been called
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][0] == "script"
        assert call_args[0][1] == "restart_device"
        assert coordinator._recovery_script_executed is True


async def test_coordinator_execute_recovery_script_failure(
    mock_hass: MagicMock,
) -> None:
    """Test recovery script execution handles errors gracefully."""
    entry = create_mock_config_entry(recovery_script="script.nonexistent")

    # Configure mock to raise error when called
    mock_hass.services.async_call = AsyncMock(side_effect=HomeAssistantError("Script not found"))

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_connection_issue",
        ),
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))
        mock_api.data = {"sn": "SN123", "mac": "AA:BB:CC:DD:EE:FF"}

        coordinator = SinapsiAlfaCoordinator(mock_hass, entry)
        coordinator._consecutive_failures = DEFAULT_FAILURES_THRESHOLD - 1

        # Should not raise additional error from script failure
        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        # Script was attempted but failed
        assert coordinator._recovery_script_executed is False


async def test_coordinator_format_downtime_seconds(
    hass: HomeAssistant,
) -> None:
    """Test _format_downtime for seconds only."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ):
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator._format_downtime(45) == "45s"
        assert coordinator._format_downtime(0) == "0s"
        assert coordinator._format_downtime(59) == "59s"


async def test_coordinator_format_downtime_minutes(
    hass: HomeAssistant,
) -> None:
    """Test _format_downtime for minutes."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ):
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator._format_downtime(60) == "1m"
        assert coordinator._format_downtime(90) == "1m 30s"
        assert coordinator._format_downtime(120) == "2m"
        assert coordinator._format_downtime(3599) == "59m 59s"


async def test_coordinator_format_downtime_hours(
    hass: HomeAssistant,
) -> None:
    """Test _format_downtime for hours."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ):
        coordinator = SinapsiAlfaCoordinator(hass, entry)

        assert coordinator._format_downtime(3600) == "1h"
        assert coordinator._format_downtime(3660) == "1h 1m"
        assert coordinator._format_downtime(7200) == "2h"
        assert coordinator._format_downtime(7320) == "2h 2m"


async def test_coordinator_fire_device_event(
    mock_hass: MagicMock,
) -> None:
    """Test _fire_device_event fires event on bus."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.data = {"sn": "SN123", "mac": "AA:BB:CC:DD:EE:FF"}

        coordinator = SinapsiAlfaCoordinator(mock_hass, entry)
        coordinator.device_id = "test_device_id"

        coordinator._fire_device_event("device_recovered", {"extra": "data"})

        mock_hass.bus.async_fire.assert_called_once()
        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][0] == f"{DOMAIN}_event"
        event_data = call_args[0][1]
        assert event_data["device_id"] == "test_device_id"
        assert event_data["type"] == "device_recovered"
        assert event_data["extra"] == "data"


async def test_coordinator_fire_device_event_no_device_id(
    mock_hass: MagicMock,
) -> None:
    """Test _fire_device_event does nothing without device_id."""
    entry = create_mock_config_entry()

    with patch(
        "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
    ):
        coordinator = SinapsiAlfaCoordinator(mock_hass, entry)
        coordinator.device_id = None  # No device ID set

        coordinator._fire_device_event("device_recovered")

        # Should not fire event
        mock_hass.bus.async_fire.assert_not_called()


async def test_coordinator_fires_device_event_on_failure_threshold(
    mock_hass: MagicMock,
) -> None:
    """Test device event is fired when failure threshold is reached."""
    entry = create_mock_config_entry()

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_connection_issue",
        ),
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))
        mock_api.data = {"sn": "", "mac": ""}

        coordinator = SinapsiAlfaCoordinator(mock_hass, entry)
        coordinator.device_id = "test_device"
        coordinator._consecutive_failures = DEFAULT_FAILURES_THRESHOLD - 1

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        # Event should be fired for device_unreachable
        mock_hass.bus.async_fire.assert_called()
        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][0] == f"{DOMAIN}_event"
        assert call_args[0][1]["type"] == "device_unreachable"


async def test_coordinator_fires_recovery_event(
    mock_hass: MagicMock,
    mock_api_data: dict,
) -> None:
    """Test device_recovered event is fired on successful recovery."""
    entry = create_mock_config_entry()

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.delete_connection_issue",
        ),
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_recovery_notification",
        ),
        patch("custom_components.sinapsi_alfa.coordinator.time") as mock_time,
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(return_value=mock_api_data)
        mock_api.data = {"sn": "", "mac": ""}
        mock_time.time.return_value = 1000.0

        coordinator = SinapsiAlfaCoordinator(mock_hass, entry)
        coordinator.device_id = "test_device"
        coordinator._repair_issue_created = True
        coordinator._consecutive_failures = 3
        coordinator._failure_start_time = 900.0

        await coordinator.async_update_data()

        # Event should be fired for device_recovered
        mock_hass.bus.async_fire.assert_called()
        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][0] == f"{DOMAIN}_event"
        assert call_args[0][1]["type"] == "device_recovered"
        assert call_args[0][1]["previous_failures"] == 3
        assert call_args[0][1]["downtime_seconds"] == 100


async def test_coordinator_repair_notification_disabled(
    hass: HomeAssistant,
) -> None:
    """Test repair issue not created when notifications disabled."""
    entry = create_mock_config_entry(enable_repair_notification=False)

    with (
        patch(
            "custom_components.sinapsi_alfa.coordinator.SinapsiAlfaAPI",
        ) as mock_api_class,
        patch(
            "custom_components.sinapsi_alfa.coordinator.create_connection_issue",
        ) as mock_create_issue,
    ):
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))
        mock_api.data = {"sn": "", "mac": ""}

        coordinator = SinapsiAlfaCoordinator(hass, entry)
        coordinator._consecutive_failures = DEFAULT_FAILURES_THRESHOLD - 1

        with pytest.raises(UpdateFailed):
            await coordinator.async_update_data()

        # Should NOT create repair issue when disabled
        mock_create_issue.assert_not_called()
        # But should still track that threshold was reached
        assert coordinator._repair_issue_created is True
