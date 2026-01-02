"""Tests for Sinapsi Alfa repairs module.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.sinapsi_alfa.const import DOMAIN
from custom_components.sinapsi_alfa.repairs import (
    ISSUE_CONNECTION_FAILED,
    ISSUE_RECOVERY_SUCCESS,
    ISSUE_RECOVERY_SUCCESS_NO_SCRIPT,
    async_create_fix_flow,
    create_connection_issue,
    create_recovery_notification,
    delete_connection_issue,
)
from homeassistant.components.repairs import ConfirmRepairFlow
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

    def test_issue_recovery_success_value(self) -> None:
        """Test ISSUE_RECOVERY_SUCCESS constant value."""
        assert ISSUE_RECOVERY_SUCCESS == "recovery_success"

    def test_issue_recovery_success_no_script_value(self) -> None:
        """Test ISSUE_RECOVERY_SUCCESS_NO_SCRIPT constant value."""
        assert ISSUE_RECOVERY_SUCCESS_NO_SCRIPT == "recovery_success_no_script"

    def test_issue_id_format(self) -> None:
        """Test issue ID format is correct."""
        entry_id = "test_123"
        expected = f"{ISSUE_CONNECTION_FAILED}_{entry_id}"
        assert expected == "connection_failed_test_123"


class TestAsyncCreateFixFlow:
    """Tests for async_create_fix_flow function."""

    @pytest.mark.asyncio
    async def test_create_fix_flow_recovery_success(self, hass: HomeAssistant) -> None:
        """Test fix flow for recovery_success issue returns ConfirmRepairFlow."""
        issue_id = f"{ISSUE_RECOVERY_SUCCESS}_entry123"
        result = await async_create_fix_flow(hass, issue_id, None)
        assert isinstance(result, ConfirmRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_recovery_success_no_script(self, hass: HomeAssistant) -> None:
        """Test fix flow for recovery_success_no_script returns ConfirmRepairFlow."""
        issue_id = f"{ISSUE_RECOVERY_SUCCESS_NO_SCRIPT}_entry456"
        result = await async_create_fix_flow(hass, issue_id, None)
        assert isinstance(result, ConfirmRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_other_issue(self, hass: HomeAssistant) -> None:
        """Test fix flow for other issues returns ConfirmRepairFlow as fallback."""
        issue_id = "some_other_issue_entry789"
        result = await async_create_fix_flow(hass, issue_id, None)
        assert isinstance(result, ConfirmRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_with_data(self, hass: HomeAssistant) -> None:
        """Test fix flow works with data parameter."""
        issue_id = f"{ISSUE_RECOVERY_SUCCESS}_entry"
        data = {"key": "value", "count": 42}
        result = await async_create_fix_flow(hass, issue_id, data)
        assert isinstance(result, ConfirmRepairFlow)


class TestCreateRecoveryNotification:
    """Tests for create_recovery_notification function."""

    def test_create_recovery_notification_with_script(self, hass: HomeAssistant) -> None:
        """Test creating recovery notification with script execution."""
        entry_id = "test_entry"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_recovery_notification(
                hass,
                entry_id,
                device_name=TEST_NAME,
                started_at="2026-01-02 10:00:00",
                ended_at="2026-01-02 10:05:00",
                downtime="5m 0s",
                script_name="script.recovery_action",
                script_executed_at="2026-01-02 10:03:00",
            )

            mock_create.assert_called_once()
            kwargs = mock_create.call_args[1]

            assert kwargs["translation_key"] == ISSUE_RECOVERY_SUCCESS
            assert kwargs["is_fixable"] is True
            assert kwargs["is_persistent"] is True
            assert kwargs["severity"] == ir.IssueSeverity.WARNING

            placeholders = kwargs["translation_placeholders"]
            assert placeholders["device_name"] == TEST_NAME
            assert placeholders["started_at"] == "2026-01-02 10:00:00"
            assert placeholders["ended_at"] == "2026-01-02 10:05:00"
            assert placeholders["downtime"] == "5m 0s"
            assert placeholders["script_name"] == "script.recovery_action"
            assert placeholders["script_executed_at"] == "2026-01-02 10:03:00"

    def test_create_recovery_notification_without_script(self, hass: HomeAssistant) -> None:
        """Test creating recovery notification without script execution."""
        entry_id = "test_entry_no_script"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_recovery_notification(
                hass,
                entry_id,
                device_name=TEST_NAME,
                started_at="2026-01-02 12:00:00",
                ended_at="2026-01-02 12:10:00",
                downtime="10m 0s",
                script_name=None,
                script_executed_at=None,
            )

            mock_create.assert_called_once()
            kwargs = mock_create.call_args[1]

            assert kwargs["translation_key"] == ISSUE_RECOVERY_SUCCESS_NO_SCRIPT
            assert kwargs["is_fixable"] is True

            placeholders = kwargs["translation_placeholders"]
            assert placeholders["device_name"] == TEST_NAME
            assert placeholders["started_at"] == "2026-01-02 12:00:00"
            assert placeholders["ended_at"] == "2026-01-02 12:10:00"
            assert placeholders["downtime"] == "10m 0s"
            # Script fields should not be present
            assert "script_name" not in placeholders
            assert "script_executed_at" not in placeholders

    def test_create_recovery_notification_issue_id_format(self, hass: HomeAssistant) -> None:
        """Test recovery notification issue ID format."""
        entry_id = "unique_entry_id"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_recovery_notification(
                hass,
                entry_id,
                device_name=TEST_NAME,
                started_at="2026-01-02 14:00:00",
                ended_at="2026-01-02 14:01:00",
                downtime="1m 0s",
            )

            # Check issue ID format
            issue_id = mock_create.call_args[0][2]
            assert entry_id in issue_id
            assert issue_id.startswith(ISSUE_RECOVERY_SUCCESS_NO_SCRIPT)
