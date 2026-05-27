"""Switch platform for RetroArch (optimistic toggles)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchSwitchDescription(SwitchEntityDescription):
    """An optimistic switch backed by a single TOGGLE command."""

    command: str


SWITCHES: tuple[RetroArchSwitchDescription, ...] = (
    RetroArchSwitchDescription(key="fast_forward", command="FAST_FORWARD"),
    RetroArchSwitchDescription(key="slow_motion", command="SLOWMOTION"),
    RetroArchSwitchDescription(key="mute", command="MUTE"),
    RetroArchSwitchDescription(key="fullscreen", command="FULLSCREEN_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchSwitchDescription(key="pause", command="PAUSE_TOGGLE"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RetroArchSwitch(coordinator, description) for description in SWITCHES)


class RetroArchSwitch(RetroArchEntity, SwitchEntity):
    """Optimistic switch: tracks an internal bool, toggles only on change."""

    entity_description: RetroArchSwitchDescription
    _attr_assumed_state = True

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchSwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self._attr_is_on:
            await self.coordinator.client.send_command(self.entity_description.command)
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._attr_is_on:
            await self.coordinator.client.send_command(self.entity_description.command)
            self._attr_is_on = False
            self.async_write_ha_state()
