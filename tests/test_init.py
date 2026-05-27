"""Tests for setup and unload of the RetroArch integration."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def test_setup_and_unload(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
