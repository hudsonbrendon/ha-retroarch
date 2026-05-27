"""Tests for RetroArch services."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", []), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="playing", game="X")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=AsyncMock(return_value=None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_send_command_service(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            DOMAIN, "send_command",
            {"config_entry_id": entry.entry_id, "command": "RESET"},
            blocking=True,
        )
    mock_send.assert_awaited_once_with("RESET")


async def test_read_memory_service_returns_data(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "async_read_memory", new=AsyncMock(return_value=[10, 20])):
        result = await hass.services.async_call(
            DOMAIN, "read_memory",
            {"config_entry_id": entry.entry_id, "address": "7e0019", "size": 2},
            blocking=True, return_response=True,
        )
    assert result["data"] == [10, 20]
    assert result["hex"] == "0a 14"


async def test_write_memory_service(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "async_write_memory", new=AsyncMock()) as mock_write:
        await hass.services.async_call(
            DOMAIN, "write_memory",
            {"config_entry_id": entry.entry_id, "address": "7e0019", "data": [10, 255]},
            blocking=True,
        )
    mock_write.assert_awaited_once_with(0x7E0019, [10, 255])


async def test_show_message_service(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            DOMAIN, "show_message",
            {"config_entry_id": entry.entry_id, "message": "Hello"},
            blocking=True,
        )
    mock_send.assert_awaited_once_with("SHOW_MSG Hello")
