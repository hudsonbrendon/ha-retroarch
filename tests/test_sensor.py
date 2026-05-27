"""Tests for RetroArch sensors."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import CONF_RAM_SENSORS, DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass, status, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, options=options or {}, unique_id="192.168.1.50:55355"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", [Platform.SENSOR]), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_read_memory",
        new=AsyncMock(return_value=[0x05]),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_game_sensor_reports_title(hass):
    status = RetroArchStatus(
        available=True, state="playing", system="nes", game="Metroid", crc32="DEADBEEF"
    )
    await _setup(hass, status)
    state = hass.states.get("sensor.retroarch_game")
    assert state.state == "Metroid"


async def test_system_sensor_reports_core(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    await _setup(hass, status)
    assert hass.states.get("sensor.retroarch_system").state == "nes"


async def test_ram_sensor_reports_value(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    options = {CONF_RAM_SENSORS: [{"name": "Lives", "address": "7e0019", "size": 1, "scale": 1.0, "unit": "lives", "signed": False, "big_endian": False}]}
    await _setup(hass, status, options)
    state = hass.states.get("sensor.retroarch_lives")
    assert state.state == "5"
    assert state.attributes["unit_of_measurement"] == "lives"
