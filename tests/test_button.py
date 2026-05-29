"""Tests for RetroArch buttons."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", [Platform.BUTTON]), patch(
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


async def test_reset_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.retroarch_reset"}, blocking=True
        )
    mock_send.assert_awaited_once_with("RESET")


async def test_screenshot_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.retroarch_screenshot"}, blocking=True
        )
    mock_send.assert_awaited_once_with("SCREENSHOT")


async def test_save_files_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.retroarch_save_sram_to_disk"}, blocking=True
        )
    mock_send.assert_awaited_once_with("SAVE_FILES")


async def test_menu_down_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.retroarch_menu_down"}, blocking=True
        )
    mock_send.assert_awaited_once_with("MENU_DOWN")


async def test_play_replay_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.retroarch_play_replay"}, blocking=True
        )
    mock_send.assert_awaited_once_with("PLAY_REPLAY")
