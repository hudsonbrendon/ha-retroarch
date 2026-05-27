"""Media player platform for RetroArch."""
from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import STATE_PAUSED, STATE_PLAYING
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RetroArchMediaPlayer(entry.runtime_data)])


class RetroArchMediaPlayer(RetroArchEntity, MediaPlayerEntity):
    """Represents the running game as a media player."""

    _attr_name = None  # use the device name
    _attr_media_content_type = MediaType.GAME
    _attr_supported_features = (
        MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_STEP
    )

    def __init__(self, coordinator: RetroArchDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_media_player"

    @property
    def state(self) -> MediaPlayerState:
        data = self.coordinator.data
        if data.state == STATE_PLAYING:
            return MediaPlayerState.PLAYING
        if data.state == STATE_PAUSED:
            return MediaPlayerState.PAUSED
        return MediaPlayerState.IDLE

    @property
    def media_title(self) -> str | None:
        return self.coordinator.data.game

    @property
    def app_name(self) -> str | None:
        return self.coordinator.data.system

    async def async_media_play(self) -> None:
        if self.coordinator.data.state == STATE_PAUSED:
            await self.coordinator.client.send_command("PAUSE_TOGGLE")

    async def async_media_pause(self) -> None:
        if self.coordinator.data.state == STATE_PLAYING:
            await self.coordinator.client.send_command("PAUSE_TOGGLE")

    async def async_media_stop(self) -> None:
        await self.coordinator.client.send_command("CLOSE_CONTENT")

    async def async_mute_volume(self, mute: bool) -> None:
        # RetroArch only exposes a mute TOGGLE; the desired `mute` state can't be set directly.
        await self.coordinator.client.send_command("MUTE")

    async def async_volume_up(self) -> None:
        await self.coordinator.client.send_command("VOLUME_UP")

    async def async_volume_down(self) -> None:
        await self.coordinator.client.send_command("VOLUME_DOWN")
