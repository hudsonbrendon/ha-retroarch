"""Binary sensor platform for RetroArch."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RetroArchStatus
from .const import STATE_PAUSED, STATE_PLAYING
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchBinaryDescription(BinarySensorEntityDescription):
    """Describes a binary sensor."""

    value_fn: Callable[[RetroArchStatus], bool]


BINARY_SENSORS: tuple[RetroArchBinaryDescription, ...] = (
    RetroArchBinaryDescription(
        key="playing",
        value_fn=lambda data: data.state == STATE_PLAYING,
    ),
    RetroArchBinaryDescription(
        key="paused",
        value_fn=lambda data: data.state == STATE_PAUSED,
    ),
    RetroArchBinaryDescription(
        key="content_loaded",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.state in (STATE_PLAYING, STATE_PAUSED),
    ),
    RetroArchBinaryDescription(
        key="menu_open",
        value_fn=lambda data: data.config.get("menu_active") == "true",
    ),
    RetroArchBinaryDescription(
        key="replay_active",
        value_fn=lambda data: data.config.get("active_replay") == "true",
    ),
    RetroArchBinaryDescription(
        key="retroachievements",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.config.get("cheevos_enable") == "true",
    ),
    RetroArchBinaryDescription(
        key="retroachievements_hardcore",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.config.get("cheevos_hardcore_mode_enable") == "true",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        RetroArchBinarySensor(coordinator, description) for description in BINARY_SENSORS
    )


class RetroArchBinarySensor(RetroArchEntity, BinarySensorEntity):
    """Binary sensor backed by the coordinator snapshot."""

    entity_description: RetroArchBinaryDescription

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchBinaryDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data)
