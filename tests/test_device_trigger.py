"""Tests for Sinapsi Alfa device triggers.

https://github.com/alexdelprete/ha-sinapsi-alfa
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.sinapsi_alfa.const import DOMAIN
from custom_components.sinapsi_alfa.device_trigger import (
    TRIGGER_SCHEMA,
    TRIGGER_TYPES,
    async_attach_trigger,
    async_get_triggers,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import HomeAssistant


def test_trigger_types_values() -> None:
    """Test TRIGGER_TYPES contains expected values."""
    assert "device_unreachable" in TRIGGER_TYPES
    assert "device_not_responding" in TRIGGER_TYPES
    assert "device_recovered" in TRIGGER_TYPES
    assert len(TRIGGER_TYPES) == 3


def test_trigger_schema_exists() -> None:
    """Test TRIGGER_SCHEMA is defined."""
    assert TRIGGER_SCHEMA is not None


async def test_get_triggers_device_not_found(hass: HomeAssistant) -> None:
    """Test returns empty list when device not found."""
    mock_registry = MagicMock()
    mock_registry.async_get.return_value = None

    with patch(
        "custom_components.sinapsi_alfa.device_trigger.dr.async_get",
        return_value=mock_registry,
    ):
        result = await async_get_triggers(hass, "nonexistent_device")

    assert result == []


async def test_get_triggers_device_wrong_domain(hass: HomeAssistant) -> None:
    """Test returns empty list when device belongs to different domain."""
    mock_device = MagicMock()
    mock_device.identifiers = {("other_domain", "device_123")}

    mock_registry = MagicMock()
    mock_registry.async_get.return_value = mock_device

    with patch(
        "custom_components.sinapsi_alfa.device_trigger.dr.async_get",
        return_value=mock_registry,
    ):
        result = await async_get_triggers(hass, "device_id")

    assert result == []


async def test_get_triggers_success(hass: HomeAssistant) -> None:
    """Test returns triggers for valid device."""
    device_id = "test_device_123"
    mock_device = MagicMock()
    mock_device.identifiers = {(DOMAIN, "AA:BB:CC:DD:EE:FF")}

    mock_registry = MagicMock()
    mock_registry.async_get.return_value = mock_device

    with patch(
        "custom_components.sinapsi_alfa.device_trigger.dr.async_get",
        return_value=mock_registry,
    ):
        result = await async_get_triggers(hass, device_id)

    # Should return one trigger for each trigger type
    assert len(result) == len(TRIGGER_TYPES)

    # Check each trigger has correct structure
    for trigger in result:
        assert trigger[CONF_PLATFORM] == "device"
        assert trigger[CONF_DOMAIN] == DOMAIN
        assert trigger[CONF_DEVICE_ID] == device_id
        assert trigger[CONF_TYPE] in TRIGGER_TYPES


async def test_get_triggers_all_types_included(hass: HomeAssistant) -> None:
    """Test all trigger types are included in result."""
    device_id = "test_device_456"
    mock_device = MagicMock()
    mock_device.identifiers = {(DOMAIN, "11:22:33:44:55:66")}

    mock_registry = MagicMock()
    mock_registry.async_get.return_value = mock_device

    with patch(
        "custom_components.sinapsi_alfa.device_trigger.dr.async_get",
        return_value=mock_registry,
    ):
        result = await async_get_triggers(hass, device_id)

    trigger_types_in_result = {t[CONF_TYPE] for t in result}
    assert trigger_types_in_result == TRIGGER_TYPES


async def test_attach_trigger_calls_event_trigger(hass: HomeAssistant) -> None:
    """Test attach_trigger delegates to event trigger."""
    config = {
        CONF_PLATFORM: "device",
        CONF_DOMAIN: DOMAIN,
        CONF_DEVICE_ID: "test_device",
        CONF_TYPE: "device_recovered",
    }
    action = AsyncMock()
    trigger_info = {"trigger_id": "test"}

    mock_unsubscribe = MagicMock()

    with (
        patch(
            "custom_components.sinapsi_alfa.device_trigger.event_trigger.TRIGGER_SCHEMA",
            return_value={},
        ),
        patch(
            "custom_components.sinapsi_alfa.device_trigger.event_trigger.async_attach_trigger",
            new_callable=AsyncMock,
            return_value=mock_unsubscribe,
        ) as mock_attach,
    ):
        result = await async_attach_trigger(hass, config, action, trigger_info)

    mock_attach.assert_called_once()
    assert result == mock_unsubscribe


async def test_attach_trigger_event_config(hass: HomeAssistant) -> None:
    """Test attach_trigger creates correct event config."""
    device_id = "my_device_id"
    trigger_type = "device_unreachable"
    config = {
        CONF_PLATFORM: "device",
        CONF_DOMAIN: DOMAIN,
        CONF_DEVICE_ID: device_id,
        CONF_TYPE: trigger_type,
    }
    action = AsyncMock()
    trigger_info = {"trigger_id": "test"}

    captured_event_config = None

    def capture_schema(config_dict):
        nonlocal captured_event_config
        captured_event_config = config_dict
        return config_dict

    with (
        patch(
            "custom_components.sinapsi_alfa.device_trigger.event_trigger.TRIGGER_SCHEMA",
            side_effect=capture_schema,
        ),
        patch(
            "custom_components.sinapsi_alfa.device_trigger.event_trigger.async_attach_trigger",
            new_callable=AsyncMock,
        ),
    ):
        await async_attach_trigger(hass, config, action, trigger_info)

    # Verify the event config structure
    assert captured_event_config is not None
    assert captured_event_config["platform"] == "event"
    assert captured_event_config["event_type"] == f"{DOMAIN}_event"
    assert captured_event_config["event_data"][CONF_DEVICE_ID] == device_id
    assert captured_event_config["event_data"][CONF_TYPE] == trigger_type
