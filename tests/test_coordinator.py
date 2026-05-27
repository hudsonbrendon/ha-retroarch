"""Tests for the RetroArch coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock

from custom_components.retroarch.api import RetroArchStatus
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


async def test_coordinator_fetches_config_once(hass):
    client = AsyncMock()
    client.async_get_status.return_value = RetroArchStatus(available=True, state="playing")
    client.async_get_version.return_value = "1.19.1"
    client.async_get_config_param.side_effect = lambda name: {
        "video_driver": "gl",
        "audio_driver": "alsa",
        "menu_driver": "ozone",
    }.get(name)

    coordinator = RetroArchDataUpdateCoordinator(
        hass, client=client, name="RetroArch", scan_interval=5, ram_sensors=[]
    )

    data = await coordinator._async_update_data()
    assert data.config["video_driver"] == "gl"
    assert data.config["menu_driver"] == "ozone"

    client.async_get_config_param.reset_mock()
    await coordinator._async_update_data()
    client.async_get_config_param.assert_not_called()
