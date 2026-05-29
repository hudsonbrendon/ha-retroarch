"""DataUpdateCoordinator for the RetroArch integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import RetroArchClient, RetroArchStatus
from .const import (
    CONF_RAM_MEMORY_MAP,
    DOMAIN,
    EVENT_GAME_CHANGED,
    EVENT_GAME_STARTED,
    EVENT_GAME_STOPPED,
    STATE_PAUSED,
    STATE_PLAYING,
)

_LOGGER = logging.getLogger(__name__)

type RetroArchConfigEntry = ConfigEntry["RetroArchDataUpdateCoordinator"]

# Live state — polled every cycle.
DYNAMIC_CONFIG_PARAMS: tuple[str, ...] = (
    "video_fullscreen",
    "menu_active",
    "active_replay",
    "audio_volume",
    "audio_mute_enable",
    "state_slot",
    "cheevos_hardcore_mode_enable",
)
# Rarely change — fetched once and cached.
STATIC_CONFIG_PARAMS: tuple[str, ...] = (
    "cheevos_enable",
    "cheevos_username",
    "netplay_nickname",
    "savefile_directory",
    "savestate_directory",
    "system_directory",
    "cache_directory",
    "log_dir",
    "runtime_log_directory",
    "video_driver",
    "audio_driver",
    "input_driver",
    "fastforward_ratio",
    "slowmotion_ratio",
)

_CONTENT_STATES = (STATE_PLAYING, STATE_PAUSED)


class RetroArchDataUpdateCoordinator(DataUpdateCoordinator[RetroArchStatus]):
    """Polls one RetroArch instance and shares a RetroArchStatus snapshot."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: RetroArchClient,
        name: str,
        scan_interval: int,
        ram_sensors: list[dict],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {name}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.device_name = name
        self.ram_sensors = ram_sensors
        self._version: str | None = None
        self._static_config: dict[str, str] | None = None
        # Transition tracking for event-bus + playtime.
        self._prev_game: str | None = None
        self._prev_available = False
        self.playing_since: datetime | None = None

    def _track_transitions(self, status: RetroArchStatus) -> None:
        """Fire game start/stop/change events and maintain playing_since."""
        game = status.game if status.state in _CONTENT_STATES else None
        prev = self._prev_game

        if game == prev:
            return

        entry_id = self.config_entry.entry_id if self.config_entry else None
        event_data = {"entry_id": entry_id, "device": self.device_name}
        if prev is None and game is not None:
            self.playing_since = dt_util.utcnow()
            self.hass.bus.async_fire(EVENT_GAME_STARTED, {**event_data, "game": game, "system": status.system})
        elif game is None and prev is not None:
            self.playing_since = None
            self.hass.bus.async_fire(EVENT_GAME_STOPPED, {**event_data, "game": prev})
        else:
            self.playing_since = dt_util.utcnow()
            self.hass.bus.async_fire(
                EVENT_GAME_CHANGED,
                {**event_data, "game": game, "system": status.system, "previous_game": prev},
            )
        self._prev_game = game

    async def _async_update_data(self) -> RetroArchStatus:
        status = await self.client.async_get_status()

        if not status.available:
            if self._prev_available:
                # Lost the connection — treat as game stopped.
                self._track_transitions(status)
                self._prev_available = False
            return status
        self._prev_available = True

        # Version rarely changes; fetch once and cache.
        if self._version is None:
            self._version = await self.client.async_get_version()
        status.version = self._version

        for param in DYNAMIC_CONFIG_PARAMS:
            value = await self.client.async_get_config_param(param)
            if value is not None:
                status.config[param] = value

        if self._static_config is None:
            self._static_config = {}
            for param in STATIC_CONFIG_PARAMS:
                value = await self.client.async_get_config_param(param)
                if value is not None:
                    self._static_config[param] = value
        status.config.update(self._static_config)

        for sensor in self.ram_sensors:
            address = int(str(sensor["address"]), 16)
            size = int(sensor["size"])
            if sensor.get(CONF_RAM_MEMORY_MAP):
                value = await self.client.async_read_memory_map(address, size)
            else:
                value = await self.client.async_read_memory(address, size)
            if value is not None:
                status.ram[sensor["name"]] = value

        self._track_transitions(status)
        return status
