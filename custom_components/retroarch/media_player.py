"""Media player platform for RetroArch."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_BOX_ART_ENABLED, CONF_BOX_ART_SYSTEM, STATE_PAUSED, STATE_PLAYING
from .thumbnails import boxart_url
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

    @property
    def media_image_url(self) -> str | None:
        options = self.coordinator.config_entry.options
        if not options.get(CONF_BOX_ART_ENABLED, True):
            return None
        data = self.coordinator.data
        return boxart_url(data.system, data.game, options.get(CONF_BOX_ART_SYSTEM) or None)

    @property
    def volume_level(self) -> float | None:
        """Real output volume from RetroArch's audio_volume (dB), as a 0..1 fraction."""
        raw = self.coordinator.data.config.get("audio_volume")
        if raw is None:
            return None
        try:
            db = float(raw)
        except ValueError:
            return None
        # Convert dB gain to a linear amplitude and clamp to 0..1.
        return max(0.0, min(1.0, 10 ** (db / 20)))

    @property
    def is_volume_muted(self) -> bool | None:
        raw = self.coordinator.data.config.get("audio_mute_enable")
        if raw is None:
            return None
        return raw == "true"

    @property
    def media_position(self) -> int | None:
        """Seconds elapsed in the current session (best-effort, no fixed duration)."""
        since: datetime | None = self.coordinator.playing_since
        if since is None or self.coordinator.data.state != STATE_PLAYING:
            return None
        return max(0, int((dt_util.utcnow() - since).total_seconds()))

    @property
    def media_position_updated_at(self) -> datetime | None:
        if self.coordinator.playing_since is None:
            return None
        return dt_util.utcnow()

    async def async_media_play(self) -> None:
        if self.coordinator.data.state == STATE_PAUSED:
            await self.coordinator.client.send_command("PAUSE_TOGGLE")

    async def async_media_pause(self) -> None:
        if self.coordinator.data.state == STATE_PLAYING:
            await self.coordinator.client.send_command("PAUSE_TOGGLE")

    async def async_media_stop(self) -> None:
        await self.coordinator.client.send_command("CLOSE_CONTENT")

    async def async_mute_volume(self, mute: bool) -> None:
        # RetroArch only exposes a mute TOGGLE. When it reports the real state via
        # audio_mute_enable, only toggle if it differs from what was requested.
        if self.is_volume_muted is mute:
            return
        await self.coordinator.client.send_command("MUTE")
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        await self.coordinator.client.send_command("VOLUME_UP")

    async def async_volume_down(self) -> None:
        await self.coordinator.client.send_command("VOLUME_DOWN")
