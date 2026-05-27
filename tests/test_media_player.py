"""Tests for the RetroArch media player."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass, status):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", [Platform.MEDIA_PLAYER]), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
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


async def test_media_player_playing_state_and_title(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    await _setup(hass, status)
    state = hass.states.get("media_player.retroarch")
    assert state.state == "playing"
    assert state.attributes["media_title"] == "Metroid"
    assert state.attributes["app_name"] == "nes"


async def test_media_player_paused_state(hass):
    status = RetroArchStatus(available=True, state="paused", system="nes", game="Metroid")
    await _setup(hass, status)
    assert hass.states.get("media_player.retroarch").state == "paused"


async def test_media_player_contentless_is_idle(hass):
    status = RetroArchStatus(available=True, state="contentless")
    await _setup(hass, status)
    assert hass.states.get("media_player.retroarch").state == "idle"


async def test_media_player_pause_sends_toggle(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    entry = await _setup(hass, status)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "media_player", "media_pause", {"entity_id": "media_player.retroarch"}, blocking=True
        )
    mock_send.assert_awaited_once_with("PAUSE_TOGGLE")


async def test_media_player_stop_closes_content(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    entry = await _setup(hass, status)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "media_player", "media_stop", {"entity_id": "media_player.retroarch"}, blocking=True
        )
    mock_send.assert_awaited_once_with("CLOSE_CONTENT")
