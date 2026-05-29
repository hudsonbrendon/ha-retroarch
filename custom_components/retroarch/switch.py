"""Switch platform for RetroArch (optimistic toggles)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RetroArchStatus
from .const import STATE_PAUSED
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchSwitchDescription(SwitchEntityDescription):
    """An optimistic switch backed by a single TOGGLE command."""

    command: str
    state_fn: Callable[[RetroArchStatus], bool | None] | None = None


SWITCHES: tuple[RetroArchSwitchDescription, ...] = (
    RetroArchSwitchDescription(key="fast_forward", command="FAST_FORWARD"),
    RetroArchSwitchDescription(key="slow_motion", command="SLOWMOTION"),
    RetroArchSwitchDescription(
        key="mute",
        command="MUTE",
        state_fn=lambda data: (data.config.get("audio_mute_enable") == "true")
        if "audio_mute_enable" in data.config
        else None,
    ),
    RetroArchSwitchDescription(
        key="fullscreen",
        command="FULLSCREEN_TOGGLE",
        entity_category=EntityCategory.CONFIG,
        state_fn=lambda data: (data.config.get("video_fullscreen") == "true")
        if "video_fullscreen" in data.config
        else None,
    ),
    RetroArchSwitchDescription(
        key="pause",
        command="PAUSE_TOGGLE",
        state_fn=lambda data: data.state == STATE_PAUSED,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RetroArchSwitch(coordinator, description) for description in SWITCHES)


class RetroArchSwitch(RetroArchEntity, SwitchEntity):
    """Switch backed by a TOGGLE command. Optimistic unless it can read real state."""

    entity_description: RetroArchSwitchDescription

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchSwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_assumed_state = description.state_fn is None
        self._optimistic = False

    @property
    def is_on(self) -> bool | None:
        if self.entity_description.state_fn is not None:
            return self.entity_description.state_fn(self.coordinator.data)
        return self._optimistic

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.is_on:
            return
        await self.coordinator.client.send_command(self.entity_description.command)
        if self.entity_description.state_fn is None:
            self._optimistic = True
            self.async_write_ha_state()
        else:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.is_on is False:
            return
        await self.coordinator.client.send_command(self.entity_description.command)
        if self.entity_description.state_fn is None:
            self._optimistic = False
            self.async_write_ha_state()
        else:
            await self.coordinator.async_request_refresh()
