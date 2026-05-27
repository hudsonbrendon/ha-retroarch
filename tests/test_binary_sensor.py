"""Tests for RetroArch binary sensors."""
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
    with patch("custom_components.retroarch.PLATFORMS", [Platform.BINARY_SENSOR]), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_playing_binary_sensor_on(hass):
    await _setup(hass, RetroArchStatus(available=True, state="playing", game="Metroid"))
    assert hass.states.get("binary_sensor.retroarch_playing").state == "on"
    assert hass.states.get("binary_sensor.retroarch_paused").state == "off"


async def test_paused_binary_sensor_on(hass):
    await _setup(hass, RetroArchStatus(available=True, state="paused", game="Metroid"))
    assert hass.states.get("binary_sensor.retroarch_playing").state == "off"
    assert hass.states.get("binary_sensor.retroarch_paused").state == "on"
