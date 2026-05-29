"""Tests for RetroArch optimistic switches."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup_status(hass, status):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", [Platform.SWITCH]), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=AsyncMock(side_effect=lambda name: status.config.get(name)),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", [Platform.SWITCH]), patch(
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


async def test_fast_forward_turn_on_sends_toggle(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.retroarch_fast_forward"}, blocking=True
        )
    mock_send.assert_awaited_once_with("FAST_FORWARD")
    assert hass.states.get("switch.retroarch_fast_forward").state == "on"


async def test_fast_forward_turn_on_twice_only_toggles_once(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.retroarch_fast_forward"}, blocking=True
        )
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.retroarch_fast_forward"}, blocking=True
        )
    assert mock_send.await_count == 1


async def test_fullscreen_on_when_config_true(hass):
    status = RetroArchStatus(available=True, state="playing", game="X", config={"video_fullscreen": "true"})
    await _setup_status(hass, status)
    assert hass.states.get("switch.retroarch_fullscreen").state == "on"


async def test_pause_switch_on_when_paused(hass):
    status = RetroArchStatus(available=True, state="paused", game="X")
    await _setup_status(hass, status)
    assert hass.states.get("switch.retroarch_pause").state == "on"


async def test_mute_switch_on_when_config_true(hass):
    status = RetroArchStatus(available=True, state="playing", game="X", config={"audio_mute_enable": "true"})
    await _setup_status(hass, status)
    assert hass.states.get("switch.retroarch_mute").state == "on"


async def test_pause_switch_turn_off_resumes(hass):
    status = RetroArchStatus(available=True, state="paused", game="X")
    entry = await _setup_status(hass, status)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": "switch.retroarch_pause"}, blocking=True
        )
    mock_send.assert_awaited_once_with("PAUSE_TOGGLE")
