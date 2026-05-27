"""Button platform for RetroArch (fire-and-forget commands)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchButtonDescription(ButtonEntityDescription):
    """A button that sends one network command."""

    command: str


BUTTONS: tuple[RetroArchButtonDescription, ...] = (
    RetroArchButtonDescription(key="pause_toggle", command="PAUSE_TOGGLE"),
    RetroArchButtonDescription(key="reset", command="RESET"),
    RetroArchButtonDescription(key="frame_advance", command="FRAMEADVANCE"),
    RetroArchButtonDescription(key="save_state", command="SAVE_STATE"),
    RetroArchButtonDescription(key="load_state", command="LOAD_STATE"),
    RetroArchButtonDescription(key="state_slot_plus", command="STATE_SLOT_PLUS"),
    RetroArchButtonDescription(key="state_slot_minus", command="STATE_SLOT_MINUS"),
    RetroArchButtonDescription(key="screenshot", command="SCREENSHOT"),
    RetroArchButtonDescription(key="fast_forward", command="FAST_FORWARD"),
    RetroArchButtonDescription(key="rewind", command="REWIND"),
    RetroArchButtonDescription(key="slow_motion", command="SLOWMOTION"),
    RetroArchButtonDescription(key="ai_service", command="AI_SERVICE"),
    RetroArchButtonDescription(key="menu_toggle", command="MENU_TOGGLE"),
    RetroArchButtonDescription(key="close_content", command="CLOSE_CONTENT"),
    RetroArchButtonDescription(key="quit", command="QUIT", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="disk_eject_toggle", command="DISK_EJECT_TOGGLE"),
    RetroArchButtonDescription(key="disk_next", command="DISK_NEXT"),
    RetroArchButtonDescription(key="disk_prev", command="DISK_PREV"),
    RetroArchButtonDescription(key="shader_next", command="SHADER_NEXT"),
    RetroArchButtonDescription(key="shader_prev", command="SHADER_PREV"),
    RetroArchButtonDescription(key="shader_toggle", command="SHADER_TOGGLE"),
    RetroArchButtonDescription(key="cheat_toggle", command="CHEAT_TOGGLE"),
    RetroArchButtonDescription(key="cheat_index_plus", command="CHEAT_INDEX_PLUS"),
    RetroArchButtonDescription(key="cheat_index_minus", command="CHEAT_INDEX_MINUS"),
    RetroArchButtonDescription(key="volume_up", command="VOLUME_UP"),
    RetroArchButtonDescription(key="volume_down", command="VOLUME_DOWN"),
    RetroArchButtonDescription(key="recording_toggle", command="RECORDING_TOGGLE"),
    RetroArchButtonDescription(key="streaming_toggle", command="STREAMING_TOGGLE"),
    RetroArchButtonDescription(key="fps_toggle", command="FPS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="statistics_toggle", command="STATISTICS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="game_focus_toggle", command="GAME_FOCUS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="grab_mouse_toggle", command="GRAB_MOUSE_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="runahead_toggle", command="RUNAHEAD_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="vrr_runloop_toggle", command="VRR_RUNLOOP_TOGGLE", entity_category=EntityCategory.CONFIG),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RetroArchButton(coordinator, description) for description in BUTTONS)


class RetroArchButton(RetroArchEntity, ButtonEntity):
    """A button that sends a single UDP command on press."""

    entity_description: RetroArchButtonDescription

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    async def async_press(self) -> None:
        await self.coordinator.client.send_command(self.entity_description.command)
