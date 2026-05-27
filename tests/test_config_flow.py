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
