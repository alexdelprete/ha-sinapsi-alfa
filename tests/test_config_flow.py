"""Tests for Sinapsi Alfa config flow."""

from unittest.mock import AsyncMock, patch

from custom_components.sinapsi_alfa.api import SinapsiConnectionError, SinapsiModbusError
from custom_components.sinapsi_alfa.config_flow import SinapsiAlfaConfigFlow
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
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import TEST_HOST, TEST_MAC, TEST_NAME


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_sinapsi_api,
    mock_setup_entry,
) -> None:
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
            CONF_SKIP_MAC_DETECTION: False,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_NAME: TEST_NAME,
        CONF_HOST: TEST_HOST,
        CONF_PORT: DEFAULT_PORT,
        CONF_SKIP_MAC_DETECTION: False,
    }
    assert result["options"] == {
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
    }


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_sinapsi_api,
    mock_setup_entry,
) -> None:
    """Test user flow when host is already configured."""
    # Create first entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
            CONF_SKIP_MAC_DETECTION: False,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Try to configure same host again
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Another Alfa",
            CONF_HOST: TEST_HOST,  # Same host
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
            CONF_SKIP_MAC_DETECTION: False,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "already_configured"}


async def test_user_flow_invalid_host(
    hass: HomeAssistant,
    mock_sinapsi_api,
) -> None:
    """Test user flow with invalid host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: "not-a-valid-host!!!",
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
            CONF_SKIP_MAC_DETECTION: False,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "invalid_host"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
) -> None:
    """Test user flow when cannot connect to device."""
    with patch(
        "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(
            side_effect=SinapsiConnectionError("Connection failed")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: DEFAULT_PORT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SKIP_MAC_DETECTION: False,
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_user_flow_modbus_error(
    hass: HomeAssistant,
) -> None:
    """Test user flow when Modbus error occurs."""
    with patch(
        "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(
            side_effect=SinapsiModbusError("Modbus read failed")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: DEFAULT_PORT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SKIP_MAC_DETECTION: False,
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_options_flow(
    hass: HomeAssistant,
    mock_sinapsi_api,
    mock_setup_entry,
) -> None:
    """Test options flow."""
    # Create config entry first
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
            CONF_SKIP_MAC_DETECTION: False,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Get the config entry
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]

    # Start options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Configure new options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: 120,
            CONF_TIMEOUT: 15,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SCAN_INTERVAL: 120,
        CONF_TIMEOUT: 15,
    }


async def test_reconfigure_flow_success(
    hass: HomeAssistant,
    mock_sinapsi_api,
    mock_setup_entry,
) -> None:
    """Test successful reconfigure flow."""
    # Create config entry first
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
            CONF_SKIP_MAC_DETECTION: False,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Get the config entry
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]

    # Start reconfigure flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # Reconfigure with new values
    new_host = "192.168.1.200"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Renamed Alfa",
            CONF_HOST: new_host,
            CONF_PORT: 503,
            CONF_SKIP_MAC_DETECTION: True,
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_flow_invalid_host(
    hass: HomeAssistant,
    mock_sinapsi_api,
    mock_setup_entry,
) -> None:
    """Test reconfigure flow with invalid host."""
    # Create config entry first
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
            CONF_SKIP_MAC_DETECTION: False,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Get the config entry
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = entries[0]

    # Start reconfigure flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    # Try invalid host
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: "invalid!!!host",
            CONF_PORT: DEFAULT_PORT,
            CONF_SKIP_MAC_DETECTION: False,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "invalid_host"}


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant,
    mock_setup_entry,
) -> None:
    """Test reconfigure flow when cannot connect."""
    # Create initial entry with mock
    with patch(
        "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.data = {"sn": TEST_MAC}
        mock_api.async_get_data = AsyncMock(return_value={"sn": TEST_MAC})

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: DEFAULT_PORT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SKIP_MAC_DETECTION: False,
            },
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY

    # Get the config entry
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = entries[0]

    # Now mock connection failure for reconfigure
    with patch(
        "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
        autospec=True,
    ) as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.async_get_data = AsyncMock(
            side_effect=SinapsiConnectionError("Connection failed")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: "192.168.1.200",
                CONF_PORT: DEFAULT_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_config_flow_version() -> None:
    """Test that config flow version is correct."""
    assert SinapsiAlfaConfigFlow.VERSION == 2
