"""Tests for Sinapsi Alfa repairs module.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.sinapsi_alfa.const import DOMAIN
from custom_components.sinapsi_alfa.repairs import (
    ISSUE_CONNECTION_FAILED,
    ISSUE_MODBUS_CONFLICT,
    NOTIFICATION_RECOVERY,
    create_connection_issue,
    create_modbus_conflict_issue,
    create_recovery_notification,
    delete_connection_issue,
    delete_modbus_conflict_issue,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT


class TestCreateConnectionIssue:
    """Tests for create_connection_issue function."""

    def test_create_connection_issue(self, hass: HomeAssistant) -> None:
        """Test creating a connection issue."""
        entry_id = "test_entry_123"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_connection_issue(
                hass,
                entry_id,
                TEST_NAME,
                TEST_HOST,
                TEST_PORT,
            )

            mock_create.assert_called_once()
            call_args = mock_create.call_args

            # Check domain
            assert call_args[0][0] == hass
            assert call_args[0][1] == DOMAIN

            # Check issue ID format
            expected_issue_id = f"{ISSUE_CONNECTION_FAILED}_{entry_id}"
            assert call_args[0][2] == expected_issue_id

            # Check keyword arguments
            kwargs = call_args[1]
            assert kwargs["is_fixable"] is False
            assert kwargs["is_persistent"] is True
            assert kwargs["severity"] == ir.IssueSeverity.ERROR
            assert kwargs["translation_key"] == ISSUE_CONNECTION_FAILED

    def test_create_connection_issue_placeholders(self, hass: HomeAssistant) -> None:
        """Test connection issue has correct placeholders."""
        entry_id = "test_entry_456"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_connection_issue(
                hass,
                entry_id,
                TEST_NAME,
                TEST_HOST,
                TEST_PORT,
            )

            kwargs = mock_create.call_args[1]
            placeholders = kwargs["translation_placeholders"]

            assert placeholders["device_name"] == TEST_NAME
            assert placeholders["host"] == TEST_HOST
            assert placeholders["port"] == str(TEST_PORT)

    def test_create_connection_issue_unique_per_entry(self, hass: HomeAssistant) -> None:
        """Test each entry gets a unique issue ID."""
        entry_id_1 = "entry_1"
        entry_id_2 = "entry_2"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_connection_issue(hass, entry_id_1, TEST_NAME, TEST_HOST, TEST_PORT)
            create_connection_issue(hass, entry_id_2, TEST_NAME, TEST_HOST, TEST_PORT)

            # Should have 2 different issue IDs
            issue_id_1 = mock_create.call_args_list[0][0][2]
            issue_id_2 = mock_create.call_args_list[1][0][2]

            assert issue_id_1 != issue_id_2
            assert entry_id_1 in issue_id_1
            assert entry_id_2 in issue_id_2


class TestDeleteConnectionIssue:
    """Tests for delete_connection_issue function."""

    def test_delete_connection_issue(self, hass: HomeAssistant) -> None:
        """Test deleting a connection issue."""
        entry_id = "test_entry_789"

        with patch.object(ir, "async_delete_issue") as mock_delete:
            delete_connection_issue(hass, entry_id)

            mock_delete.assert_called_once()
            call_args = mock_delete.call_args

            # Check domain and issue ID
            assert call_args[0][0] == hass
            assert call_args[0][1] == DOMAIN

            expected_issue_id = f"{ISSUE_CONNECTION_FAILED}_{entry_id}"
            assert call_args[0][2] == expected_issue_id

    def test_delete_connection_issue_correct_id_format(self, hass: HomeAssistant) -> None:
        """Test delete uses same ID format as create."""
        entry_id = "matching_entry"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_connection_issue(hass, entry_id, TEST_NAME, TEST_HOST, TEST_PORT)
            created_issue_id = mock_create.call_args[0][2]

        with patch.object(ir, "async_delete_issue") as mock_delete:
            delete_connection_issue(hass, entry_id)
            deleted_issue_id = mock_delete.call_args[0][2]

        # Issue IDs should match
        assert created_issue_id == deleted_issue_id


class TestIssueConstants:
    """Tests for issue constants."""

    def test_issue_connection_failed_value(self) -> None:
        """Test ISSUE_CONNECTION_FAILED constant value."""
        assert ISSUE_CONNECTION_FAILED == "connection_failed"

    def test_issue_modbus_conflict_value(self) -> None:
        """Test ISSUE_MODBUS_CONFLICT constant value."""
        assert ISSUE_MODBUS_CONFLICT == "modbus_conflict"

    def test_notification_recovery_value(self) -> None:
        """Test NOTIFICATION_RECOVERY constant value."""
        assert NOTIFICATION_RECOVERY == "recovery"

    def test_issue_id_format(self) -> None:
        """Test issue ID format is correct."""
        entry_id = "test_123"
        expected = f"{ISSUE_CONNECTION_FAILED}_{entry_id}"
        assert expected == "connection_failed_test_123"

    def test_modbus_conflict_issue_id_format(self) -> None:
        """Test modbus conflict issue ID format is correct."""
        entry_id = "test_123"
        expected = f"{ISSUE_MODBUS_CONFLICT}_{entry_id}"
        assert expected == "modbus_conflict_test_123"

    def test_notification_id_format(self) -> None:
        """Test notification ID format is correct."""
        entry_id = "test_456"
        expected = f"{DOMAIN}_{NOTIFICATION_RECOVERY}_{entry_id}"
        assert expected == "sinapsi_alfa_recovery_test_456"


class TestCreateModbusConflictIssue:
    """Tests for create_modbus_conflict_issue function."""

    def test_create_modbus_conflict_issue(self, hass: HomeAssistant) -> None:
        """Test creating a modbus conflict issue."""
        entry_id = "test_entry_123"
        modbus_host = "192.168.1.100"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_modbus_conflict_issue(
                hass,
                entry_id,
                TEST_NAME,
                TEST_HOST,
                modbus_host,
            )

            mock_create.assert_called_once()
            call_args = mock_create.call_args

            # Check domain
            assert call_args[0][0] == hass
            assert call_args[0][1] == DOMAIN

            # Check issue ID format
            expected_issue_id = f"{ISSUE_MODBUS_CONFLICT}_{entry_id}"
            assert call_args[0][2] == expected_issue_id

            # Check keyword arguments
            kwargs = call_args[1]
            assert kwargs["is_fixable"] is False
            assert kwargs["is_persistent"] is True
            assert kwargs["severity"] == ir.IssueSeverity.ERROR
            assert kwargs["translation_key"] == ISSUE_MODBUS_CONFLICT

    def test_create_modbus_conflict_issue_placeholders(self, hass: HomeAssistant) -> None:
        """Test modbus conflict issue has correct placeholders."""
        entry_id = "test_entry_456"
        modbus_host = "alfa.local"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_modbus_conflict_issue(
                hass,
                entry_id,
                TEST_NAME,
                TEST_HOST,
                modbus_host,
            )

            kwargs = mock_create.call_args[1]
            placeholders = kwargs["translation_placeholders"]

            assert placeholders["device_name"] == TEST_NAME
            assert placeholders["host"] == TEST_HOST
            assert placeholders["modbus_host"] == modbus_host

    def test_create_modbus_conflict_issue_unique_per_entry(self, hass: HomeAssistant) -> None:
        """Test each entry gets a unique modbus conflict issue ID."""
        entry_id_1 = "entry_1"
        entry_id_2 = "entry_2"
        modbus_host = "192.168.1.100"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_modbus_conflict_issue(hass, entry_id_1, TEST_NAME, TEST_HOST, modbus_host)
            create_modbus_conflict_issue(hass, entry_id_2, TEST_NAME, TEST_HOST, modbus_host)

            # Should have 2 different issue IDs
            issue_id_1 = mock_create.call_args_list[0][0][2]
            issue_id_2 = mock_create.call_args_list[1][0][2]

            assert issue_id_1 != issue_id_2
            assert entry_id_1 in issue_id_1
            assert entry_id_2 in issue_id_2


class TestDeleteModbusConflictIssue:
    """Tests for delete_modbus_conflict_issue function."""

    def test_delete_modbus_conflict_issue(self, hass: HomeAssistant) -> None:
        """Test deleting a modbus conflict issue."""
        entry_id = "test_entry_789"

        with patch.object(ir, "async_delete_issue") as mock_delete:
            delete_modbus_conflict_issue(hass, entry_id)

            mock_delete.assert_called_once()
            call_args = mock_delete.call_args

            # Check domain and issue ID
            assert call_args[0][0] == hass
            assert call_args[0][1] == DOMAIN

            expected_issue_id = f"{ISSUE_MODBUS_CONFLICT}_{entry_id}"
            assert call_args[0][2] == expected_issue_id

    def test_delete_modbus_conflict_issue_correct_id_format(self, hass: HomeAssistant) -> None:
        """Test delete uses same ID format as create."""
        entry_id = "matching_entry"
        modbus_host = "192.168.1.100"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_modbus_conflict_issue(hass, entry_id, TEST_NAME, TEST_HOST, modbus_host)
            created_issue_id = mock_create.call_args[0][2]

        with patch.object(ir, "async_delete_issue") as mock_delete:
            delete_modbus_conflict_issue(hass, entry_id)
            deleted_issue_id = mock_delete.call_args[0][2]

        # Issue IDs should match
        assert created_issue_id == deleted_issue_id


class TestCreateRecoveryNotification:
    """Tests for create_recovery_notification function."""

    def test_create_recovery_notification_with_script(self, mock_hass: MagicMock) -> None:
        """Test creating recovery notification with script execution."""
        entry_id = "test_entry"

        create_recovery_notification(
            mock_hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="10:00:00",
            ended_at="10:05:00",
            downtime="5m 0s",
            script_name="script.recovery_action",
            script_executed_at="10:03:00",
        )

        # Verify async_create_task was called
        mock_hass.async_create_task.assert_called_once()

    def test_create_recovery_notification_without_script(self, mock_hass: MagicMock) -> None:
        """Test creating recovery notification without script execution."""
        entry_id = "test_entry_no_script"

        create_recovery_notification(
            mock_hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="12:00:00",
            ended_at="12:10:00",
            downtime="10m 0s",
            script_name=None,
            script_executed_at=None,
        )

        # Verify async_create_task was called
        mock_hass.async_create_task.assert_called_once()

    def test_create_recovery_notification_message_with_script(self, mock_hass: MagicMock) -> None:
        """Test recovery notification message content with script."""
        entry_id = "test_entry"

        # Make async_create_task execute the coroutine immediately
        mock_hass.async_create_task = lambda coro: coro

        create_recovery_notification(
            mock_hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="10:00:00",
            ended_at="10:05:00",
            downtime="5m 0s",
            script_name="script.recovery_action",
            script_executed_at="10:03:00",
        )

        # Verify service was called with correct parameters
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args

        assert call_args.kwargs["domain"] == "persistent_notification"
        assert call_args.kwargs["service"] == "create"

        service_data = call_args.kwargs["service_data"]
        assert service_data["title"] == f"{TEST_NAME} has recovered"
        assert f"{DOMAIN}_{NOTIFICATION_RECOVERY}_{entry_id}" == service_data["notification_id"]
        assert "script.recovery_action" in service_data["message"]
        assert "10:03:00" in service_data["message"]

    def test_create_recovery_notification_message_without_script(
        self, mock_hass: MagicMock
    ) -> None:
        """Test recovery notification message content without script."""
        entry_id = "test_entry_no_script"

        # Make async_create_task execute the coroutine immediately
        mock_hass.async_create_task = lambda coro: coro

        create_recovery_notification(
            mock_hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="12:00:00",
            ended_at="12:10:00",
            downtime="10m 0s",
            script_name=None,
            script_executed_at=None,
        )

        # Verify service was called with correct parameters
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args

        assert call_args.kwargs["domain"] == "persistent_notification"
        assert call_args.kwargs["service"] == "create"

        service_data = call_args.kwargs["service_data"]
        assert service_data["title"] == f"{TEST_NAME} has recovered"
        assert "12:00:00" in service_data["message"]
        assert "12:10:00" in service_data["message"]
        assert "10m 0s" in service_data["message"]
        # Script info should not be in message
        assert "Script executed" not in service_data["message"]

    def test_create_recovery_notification_id_format(self, mock_hass: MagicMock) -> None:
        """Test recovery notification ID format."""
        entry_id = "unique_entry_id"

        # Make async_create_task execute the coroutine immediately
        mock_hass.async_create_task = lambda coro: coro

        create_recovery_notification(
            mock_hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="14:00:00",
            ended_at="14:01:00",
            downtime="1m 0s",
        )

        # Check notification ID format
        call_args = mock_hass.services.async_call.call_args
        notification_id = call_args.kwargs["service_data"]["notification_id"]
        assert entry_id in notification_id
        assert notification_id == f"{DOMAIN}_{NOTIFICATION_RECOVERY}_{entry_id}"
