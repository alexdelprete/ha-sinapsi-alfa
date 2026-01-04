"""Tests for Sinapsi Alfa config flow."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from custom_components.sinapsi_alfa.api import SinapsiConnectionError, SinapsiModbusError
from custom_components.sinapsi_alfa.config_flow import (
    SinapsiAlfaConfigFlow,
    SinapsiAlfaOptionsFlow,
    get_host_from_config,
)
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


@pytest.fixture(name="sinapsi_setup", autouse=True)
def sinapsi_setup_fixture():
    """Mock sinapsi_alfa entry setup to avoid loading the full integration."""
    with patch(
        "custom_components.sinapsi_alfa.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_sinapsi_api,
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
    await hass.async_block_till_done()

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
    await hass.async_block_till_done()
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
        mock_api.async_get_data = AsyncMock(side_effect=SinapsiConnectionError("Connection failed"))

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
        mock_api.async_get_data = AsyncMock(side_effect=SinapsiModbusError("Modbus read failed"))

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
    await hass.async_block_till_done()
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
    await hass.async_block_till_done()
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
    await hass.async_block_till_done()
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
        await hass.async_block_till_done()
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
        mock_api.async_get_data = AsyncMock(side_effect=SinapsiConnectionError("Connection failed"))

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
    assert SinapsiAlfaConfigFlow.VERSION == 3


# =============================================================================
# Direct Unit Tests (No Integration Loading Required)
# =============================================================================
# These tests instantiate the config flow class directly and mock the hass object,
# avoiding HA's integration loading mechanism that fails in CI environments.


class TestGetHostFromConfig:
    """Tests for get_host_from_config function."""

    async def test_get_host_from_config_empty(self, mock_hass: MagicMock) -> None:
        """Test get_host_from_config with no entries."""
        mock_hass.config_entries.async_entries.return_value = []
        result = get_host_from_config(mock_hass)
        assert result == set()

    async def test_get_host_from_config_with_entries(self, mock_hass: MagicMock) -> None:
        """Test get_host_from_config with existing entries."""
        # Create mock config entries
        entry1 = MagicMock()
        entry1.data = {CONF_HOST: "192.168.1.100"}
        entry2 = MagicMock()
        entry2.data = {CONF_HOST: "192.168.1.101"}
        entry3 = MagicMock()
        entry3.data = {}  # Entry without host

        mock_hass.config_entries.async_entries.return_value = [entry1, entry2, entry3]
        result = get_host_from_config(mock_hass)

        assert result == {"192.168.1.100", "192.168.1.101", None}
        mock_hass.config_entries.async_entries.assert_called_once_with(DOMAIN)


class TestHostInConfigurationExists:
    """Tests for _host_in_configuration_exists method."""

    async def test_host_exists_true(self, mock_hass: MagicMock) -> None:
        """Test that existing host is detected."""
        entry = MagicMock()
        entry.data = {CONF_HOST: TEST_HOST}
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass

        assert flow._host_in_configuration_exists(TEST_HOST) is True

    async def test_host_exists_false(self, mock_hass: MagicMock) -> None:
        """Test that non-existing host is not detected."""
        entry = MagicMock()
        entry.data = {CONF_HOST: "192.168.1.200"}
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass

        assert flow._host_in_configuration_exists(TEST_HOST) is False

    async def test_host_exists_empty_config(self, mock_hass: MagicMock) -> None:
        """Test with no config entries."""
        mock_hass.config_entries.async_entries.return_value = []

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass

        assert flow._host_in_configuration_exists(TEST_HOST) is False

    async def test_host_exists_none(self, mock_hass: MagicMock) -> None:
        """Test checking for None host."""
        entry = MagicMock()
        entry.data = {}  # No host key
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass

        # None will be in the set from entries without host
        assert flow._host_in_configuration_exists(None) is True


class TestTestConnection:
    """Tests for _test_connection method."""

    async def test_connection_success(self, mock_hass: MagicMock, mock_api_data: dict) -> None:
        """Test successful connection returns serial number."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = mock_api_data
            mock_api.async_get_data = AsyncMock(return_value=True)

            result = await flow._test_connection(
                TEST_NAME, TEST_HOST, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_TIMEOUT, False
            )

            assert result == TEST_MAC
            mock_api_class.assert_called_once_with(
                mock_hass,
                TEST_NAME,
                TEST_HOST,
                DEFAULT_PORT,
                DEFAULT_SCAN_INTERVAL,
                DEFAULT_TIMEOUT,
                False,
            )
            mock_api.async_get_data.assert_awaited_once()

    async def test_connection_error(self, mock_hass: MagicMock) -> None:
        """Test SinapsiConnectionError returns None."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=SinapsiConnectionError("Connection refused")
            )

            result = await flow._test_connection(
                TEST_NAME, TEST_HOST, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_TIMEOUT, False
            )

            assert result is None

    async def test_modbus_error(self, mock_hass: MagicMock) -> None:
        """Test SinapsiModbusError returns None."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=SinapsiModbusError("Modbus read failed")
            )

            result = await flow._test_connection(
                TEST_NAME, TEST_HOST, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_TIMEOUT, False
            )

            assert result is None


class TestAsyncStepUserDirect:
    """Direct tests for async_step_user without full integration loading."""

    async def test_async_step_user_shows_form(self, mock_hass: MagicMock) -> None:
        """Test initial form is shown when no user_input."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}

        result = await flow.async_step_user(None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_async_step_user_already_configured(self, mock_hass: MagicMock) -> None:
        """Test error when host is already configured."""
        # Setup existing entry
        entry = MagicMock()
        entry.data = {CONF_HOST: TEST_HOST}
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}

        result = await flow.async_step_user(
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: DEFAULT_PORT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SKIP_MAC_DETECTION: False,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "already_configured"}

    async def test_async_step_user_invalid_host(self, mock_hass: MagicMock) -> None:
        """Test error when host is invalid."""
        mock_hass.config_entries.async_entries.return_value = []

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}

        result = await flow.async_step_user(
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: "not a valid host!@#",
                CONF_PORT: DEFAULT_PORT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SKIP_MAC_DETECTION: False,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "invalid_host"}

    async def test_async_step_user_cannot_connect(self, mock_hass: MagicMock) -> None:
        """Test error when connection fails."""
        mock_hass.config_entries.async_entries.return_value = []

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=SinapsiConnectionError("Connection failed")
            )

            result = await flow.async_step_user(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_TIMEOUT: DEFAULT_TIMEOUT,
                    CONF_SKIP_MAC_DETECTION: False,
                }
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}

    async def test_async_step_user_success(self, mock_hass: MagicMock, mock_api_data: dict) -> None:
        """Test successful config entry creation."""
        mock_hass.config_entries.async_entries.return_value = []

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}
        # Mock unique_id methods to prevent AbortFlow
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = mock_api_data
            mock_api.async_get_data = AsyncMock(return_value=True)

            result = await flow.async_step_user(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_TIMEOUT: DEFAULT_TIMEOUT,
                    CONF_SKIP_MAC_DETECTION: False,
                }
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


class TestAsyncStepReconfigureDirect:
    """Direct tests for async_step_reconfigure without full integration loading."""

    def _create_mock_reconfigure_entry(self) -> MagicMock:
        """Create a mock config entry for reconfigure tests."""
        entry = MagicMock()
        entry.data = {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_SKIP_MAC_DETECTION: False,
        }
        entry.options = {
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
        }
        entry.unique_id = TEST_MAC
        return entry

    async def test_async_step_reconfigure_shows_form(self, mock_hass: MagicMock) -> None:
        """Test initial reconfigure form is shown."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = self._create_mock_reconfigure_entry()
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        result = await flow.async_step_reconfigure(None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"] == {}

    async def test_async_step_reconfigure_invalid_host(self, mock_hass: MagicMock) -> None:
        """Test error when reconfigure host is invalid."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = self._create_mock_reconfigure_entry()
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        result = await flow.async_step_reconfigure(
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: "invalid!host@#$",
                CONF_PORT: DEFAULT_PORT,
                CONF_SKIP_MAC_DETECTION: False,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "invalid_host"}

    async def test_async_step_reconfigure_cannot_connect(self, mock_hass: MagicMock) -> None:
        """Test error when reconfigure connection fails."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = self._create_mock_reconfigure_entry()
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=SinapsiConnectionError("Connection failed")
            )

            result = await flow.async_step_reconfigure(
                {
                    CONF_NAME: "New Name",
                    CONF_HOST: "192.168.1.200",
                    CONF_PORT: 503,
                    CONF_SKIP_MAC_DETECTION: False,
                }
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}

    async def test_async_step_reconfigure_success(
        self, mock_hass: MagicMock, mock_api_data: dict
    ) -> None:
        """Test successful reconfiguration."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = self._create_mock_reconfigure_entry()
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_mismatch = MagicMock()
        flow.async_update_reload_and_abort = MagicMock(
            return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}
        )

        new_host = "192.168.1.200"
        new_port = 503
        new_name = "New Device Name"

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = mock_api_data
            mock_api.async_get_data = AsyncMock(return_value=True)

            await flow.async_step_reconfigure(
                {
                    CONF_NAME: new_name,
                    CONF_HOST: new_host,
                    CONF_PORT: new_port,
                    CONF_SKIP_MAC_DETECTION: True,
                }
            )

        # Verify the flow completed successfully
        flow.async_set_unique_id.assert_awaited_once_with(TEST_MAC)
        flow._abort_if_unique_id_mismatch.assert_called_once()
        flow.async_update_reload_and_abort.assert_called_once_with(
            mock_entry,
            title=new_name,
            data_updates={
                CONF_NAME: new_name,
                CONF_HOST: new_host,
                CONF_PORT: new_port,
                CONF_SKIP_MAC_DETECTION: True,
            },
        )


class TestOptionsFlowDirect:
    """Direct tests for SinapsiAlfaOptionsFlow without full integration loading."""

    def _create_mock_config_entry(self) -> MagicMock:
        """Create a mock config entry for options flow tests."""
        entry = MagicMock()
        entry.data = {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_SKIP_MAC_DETECTION: False,
        }
        entry.options = {
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
        }
        entry.entry_id = "test_entry_id"
        return entry

    async def test_options_flow_shows_form(self) -> None:
        """Test initial options form is shown."""
        mock_entry = self._create_mock_config_entry()

        flow = SinapsiAlfaOptionsFlow()
        # Use PropertyMock to mock the read-only config_entry property
        with patch.object(
            type(flow), "config_entry", new_callable=PropertyMock, return_value=mock_entry
        ):
            result = await flow.async_step_init(None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_saves_options(self) -> None:
        """Test options are saved correctly."""
        mock_entry = self._create_mock_config_entry()

        flow = SinapsiAlfaOptionsFlow()
        with patch.object(
            type(flow), "config_entry", new_callable=PropertyMock, return_value=mock_entry
        ):
            new_scan_interval = 120
            new_timeout = 15
            result = await flow.async_step_init(
                {
                    CONF_SCAN_INTERVAL: new_scan_interval,
                    CONF_TIMEOUT: new_timeout,
                }
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_SCAN_INTERVAL: new_scan_interval,
            CONF_TIMEOUT: new_timeout,
        }


class TestConfigFlowAttributes:
    """Test ConfigFlow class attributes."""

    def test_config_flow_version(self) -> None:
        """Test ConfigFlow VERSION is set correctly."""
        assert SinapsiAlfaConfigFlow.VERSION == 3

    def test_config_flow_connection_class(self) -> None:
        """Test ConfigFlow CONNECTION_CLASS is set correctly."""
        assert SinapsiAlfaConfigFlow.CONNECTION_CLASS == config_entries.CONN_CLASS_LOCAL_POLL

    def test_config_flow_domain(self) -> None:
        """Test ConfigFlow domain is sinapsi_alfa."""
        assert DOMAIN == "sinapsi_alfa"

    def test_async_get_options_flow_returns_options_flow(self) -> None:
        """Test async_get_options_flow returns correct type."""
        mock_entry = MagicMock()
        result = SinapsiAlfaConfigFlow.async_get_options_flow(mock_entry)
        assert isinstance(result, SinapsiAlfaOptionsFlow)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_user_step_with_none_host_in_config(
        self, mock_hass: MagicMock, mock_api_data: dict
    ) -> None:
        """Test user step when existing entry has None host."""
        entry = MagicMock()
        entry.data = {}  # No host key results in None
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}
        # Mock unique_id methods
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = mock_api_data
            mock_api.async_get_data = AsyncMock(return_value=True)

            result = await flow.async_step_user(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_TIMEOUT: DEFAULT_TIMEOUT,
                    CONF_SKIP_MAC_DETECTION: False,
                }
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY

    async def test_reconfigure_without_options(self, mock_hass: MagicMock) -> None:
        """Test reconfigure when entry has empty options."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_SKIP_MAC_DETECTION: False,
        }
        mock_entry.options = {}  # No options - should use defaults
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=SinapsiConnectionError("Connection failed")
            )

            # Should use defaults when not in options
            result = await flow.async_step_reconfigure(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_SKIP_MAC_DETECTION: False,
                }
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}

    async def test_test_connection_returns_string_serial(self, mock_hass: MagicMock) -> None:
        """Test _test_connection converts serial number to string."""
        flow = SinapsiAlfaConfigFlow()
        flow.hass = mock_hass

        with patch(
            "custom_components.sinapsi_alfa.config_flow.SinapsiAlfaAPI",
            autospec=True,
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            # Use integer serial number
            mock_api.data = {"sn": 123456789}
            mock_api.async_get_data = AsyncMock(return_value=True)

            result = await flow._test_connection(
                TEST_NAME, TEST_HOST, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_TIMEOUT, False
            )

            # Should be converted to string
            assert result == "123456789"
            assert isinstance(result, str)
