"""Tests for the RetroArch state-slot number entity."""
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
    with patch("custom_components.retroarch.PLATFORMS", [Platform.NUMBER]), patch(
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


async def test_state_slot_reads_current(hass):
    status = RetroArchStatus(available=True, state="playing", game="X", config={"state_slot": "3"})
    await _setup(hass, status)
    assert hass.states.get("number.retroarch_state_slot").state == "3.0"


async def test_state_slot_steps_to_target(hass):
    status = RetroArchStatus(available=True, state="playing", game="X", config={"state_slot": "1"})
    entry = await _setup(hass, status)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.retroarch_state_slot", "value": 3},
            blocking=True,
        )
    # 1 -> 3 means two STATE_SLOT_PLUS commands.
    assert mock_send.await_count == 2
    mock_send.assert_awaited_with("STATE_SLOT_PLUS")
