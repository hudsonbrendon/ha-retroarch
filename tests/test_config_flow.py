"""Tests for the RetroArch config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def test_menu_then_manual_success(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.MENU

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "manual"

    with patch(
        "custom_components.retroarch.config_flow.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "RetroArch"
    assert result["data"] == MOCK_CONFIG


async def test_manual_cannot_connect(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    with patch(
        "custom_components.retroarch.config_flow.RetroArchClient.async_get_version",
        new=AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_discovery_flow_success(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.retroarch.config_flow.async_discover",
        new=AsyncMock(return_value={"192.168.1.50": "1.19.1"}),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "discover"}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "discover"

    with patch(
        "custom_components.retroarch.config_flow.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "192.168.1.50", "port": 55355, "name": "RetroArch"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "192.168.1.50"


async def test_discovery_empty_falls_back_to_manual(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.retroarch.config_flow.async_discover",
        new=AsyncMock(return_value={}),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "discover"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "manual"


from unittest.mock import AsyncMock as _AsyncMock  # alias to avoid shadowing above

from homeassistant.const import CONF_SCAN_INTERVAL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import CONF_BOX_ART_ENABLED, CONF_RAM_SENSORS


async def _load_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_options_add_ram_sensor(hass):
    entry = await _load_entry(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_read_memory",
        new=_AsyncMock(return_value=[1]),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_ram_sensor"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Lives",
                "address": "7e0019",
                "size": 1,
                "signed": False,
                "big_endian": False,
                "scale": 1.0,
                "unit": "lives",
            },
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_RAM_SENSORS][0]["name"] == "Lives"


async def test_options_remove_ram_sensor(hass):
    entry = await _load_entry(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_read_memory",
        new=_AsyncMock(return_value=[1]),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_ram_sensor"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Lives",
                "address": "7e0019",
                "size": 1,
                "signed": False,
                "big_endian": False,
                "scale": 1.0,
                "unit": "lives",
            },
        )
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "remove_ram_sensor"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"name": "Lives"}
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_RAM_SENSORS] == []


async def test_options_remove_ram_sensor_none_aborts(hass):
    entry = await _load_entry(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "remove_ram_sensor"}
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_ram_sensors"


async def test_options_settings_changes_interval(hass):
    entry = await _load_entry(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "settings"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 10}
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_SCAN_INTERVAL] == 10


async def test_options_box_art(hass):
    entry = await _load_entry(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "box_art"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"box_art_enabled": False, "box_art_system": ""}
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_BOX_ART_ENABLED] is False


from homeassistant.const import CONF_HOST


async def test_reconfigure_updates_host(hass):
    entry = await _load_entry(hass)
    try:
        result = await entry.start_reconfigure_flow(hass)
    except AttributeError:
        from homeassistant.config_entries import SOURCE_RECONFIGURE
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.retroarch.config_flow.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "192.168.1.99", "port": 55355, "name": "RetroArch"},
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "192.168.1.99"
