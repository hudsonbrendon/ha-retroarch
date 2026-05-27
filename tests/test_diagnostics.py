"""Tests for RetroArch diagnostics."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN
from custom_components.retroarch.diagnostics import async_get_config_entry_diagnostics

from .const import MOCK_CONFIG


async def test_diagnostics_redacts_host(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", []), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=AsyncMock(return_value=None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["data"]["host"] == "**REDACTED**"
    assert diag["status"]["game"] == "Metroid"
    assert diag["status"]["state"] == "playing"
