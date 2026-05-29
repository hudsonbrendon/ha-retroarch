"""Tests for the RetroArch coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import (
    EVENT_GAME_CHANGED,
    EVENT_GAME_STARTED,
    EVENT_GAME_STOPPED,
)
from custom_components.retroarch.coordinator import RetroArchDataUpdateCoordinator


async def test_coordinator_merges_status_version_and_ram(hass):
    client = AsyncMock()
    client.async_get_status.return_value = RetroArchStatus(
        available=True, state="playing", system="nes", game="Metroid", crc32="DEADBEEF"
    )
    client.async_get_version.return_value = "1.19.1"
    client.async_read_memory.return_value = [0x0A]

    coordinator = RetroArchDataUpdateCoordinator(
        hass,
        client=client,
        name="RetroArch",
        scan_interval=5,
        ram_sensors=[{"name": "Lives", "address": "7e0019", "size": 1}],
    )

    data = await coordinator._async_update_data()

    assert data.available is True
    assert data.game == "Metroid"
    assert data.version == "1.19.1"
    assert data.ram["Lives"] == [0x0A]


async def test_coordinator_skips_version_when_unavailable(hass):
    client = AsyncMock()
    client.async_get_status.return_value = RetroArchStatus(available=False, state="unknown")

    coordinator = RetroArchDataUpdateCoordinator(
        hass, client=client, name="RetroArch", scan_interval=5, ram_sensors=[]
    )

    data = await coordinator._async_update_data()

    assert data.available is False
    client.async_get_version.assert_not_called()
    client.async_read_memory.assert_not_called()


async def test_coordinator_config_dynamic_and_static(hass):
    client = AsyncMock()
    client.async_get_status.return_value = RetroArchStatus(available=True, state="playing")
    client.async_get_version.return_value = "1.19.1"
    values = {
        "video_fullscreen": "true",
        "menu_active": "false",
        "active_replay": "false",
        "cheevos_enable": "true",
        "netplay_nickname": "RetroFan",
        "savestate_directory": "/states",
    }
    client.async_get_config_param.side_effect = lambda name: values.get(name)

    coordinator = RetroArchDataUpdateCoordinator(
        hass, client=client, name="RetroArch", scan_interval=5, ram_sensors=[]
    )

    data = await coordinator._async_update_data()
    assert data.config["video_fullscreen"] == "true"
    assert data.config["netplay_nickname"] == "RetroFan"

    client.async_get_config_param.reset_mock()
    await coordinator._async_update_data()
    queried = {c.args[0] for c in client.async_get_config_param.call_args_list}
    assert "video_fullscreen" in queried        # dynamic: re-queried every cycle
    assert "netplay_nickname" not in queried     # static: cached after first fetch


async def test_coordinator_uses_memory_map_when_requested(hass):
    client = AsyncMock()
    client.async_get_status.return_value = RetroArchStatus(available=True, state="playing", game="X")
    client.async_get_version.return_value = "1.19.1"
    client.async_get_config_param.return_value = None
    client.async_read_memory_map.return_value = [0x42]

    coordinator = RetroArchDataUpdateCoordinator(
        hass, client=client, name="RetroArch", scan_interval=5,
        ram_sensors=[{"name": "HP", "address": "8000", "size": 1, "memory_map": True}],
    )
    data = await coordinator._async_update_data()
    assert data.ram["HP"] == [0x42]
    client.async_read_memory_map.assert_awaited_once()
    client.async_read_memory.assert_not_called()


async def test_coordinator_fires_game_events(hass):
    client = AsyncMock()
    client.async_get_version.return_value = "1.19.1"
    client.async_get_config_param.return_value = None
    coordinator = RetroArchDataUpdateCoordinator(
        hass, client=client, name="RetroArch", scan_interval=5, ram_sensors=[]
    )

    started = async_capture_events(hass, EVENT_GAME_STARTED)
    changed = async_capture_events(hass, EVENT_GAME_CHANGED)
    stopped = async_capture_events(hass, EVENT_GAME_STOPPED)

    client.async_get_status.return_value = RetroArchStatus(available=True, state="playing", game="Metroid", system="nes")
    await coordinator._async_update_data()
    assert coordinator.playing_since is not None

    client.async_get_status.return_value = RetroArchStatus(available=True, state="playing", game="Contra", system="nes")
    await coordinator._async_update_data()

    client.async_get_status.return_value = RetroArchStatus(available=True, state="contentless")
    await coordinator._async_update_data()
    await hass.async_block_till_done()

    assert len(started) == 1 and started[0].data["game"] == "Metroid"
    assert len(changed) == 1 and changed[0].data["previous_game"] == "Metroid"
    assert len(stopped) == 1
    assert coordinator.playing_since is None
