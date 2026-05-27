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
    RetroArchButtonDescription(key="pause_toggle", name="Pause/Resume", command="PAUSE_TOGGLE"),
    RetroArchButtonDescription(key="reset", name="Reset", command="RESET"),
    RetroArchButtonDescription(key="frame_advance", name="Frame advance", command="FRAMEADVANCE"),
    RetroArchButtonDescription(key="save_state", name="Save state", command="SAVE_STATE"),
    RetroArchButtonDescription(key="load_state", name="Load state", command="LOAD_STATE"),
    RetroArchButtonDescription(key="state_slot_plus", name="State slot +", command="STATE_SLOT_PLUS"),
    RetroArchButtonDescription(key="state_slot_minus", name="State slot -", command="STATE_SLOT_MINUS"),
    RetroArchButtonDescription(key="screenshot", name="Screenshot", command="SCREENSHOT"),
    RetroArchButtonDescription(key="fast_forward", name="Fast forward toggle", command="FAST_FORWARD"),
    RetroArchButtonDescription(key="rewind", name="Rewind", command="REWIND"),
    RetroArchButtonDescription(key="slow_motion", name="Slow motion", command="SLOWMOTION"),
    RetroArchButtonDescription(key="ai_service", name="AI service", command="AI_SERVICE"),
    RetroArchButtonDescription(key="menu_toggle", name="Menu toggle", command="MENU_TOGGLE"),
    RetroArchButtonDescription(key="close_content", name="Close content", command="CLOSE_CONTENT"),
    RetroArchButtonDescription(key="quit", name="Quit RetroArch", command="QUIT", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="disk_eject_toggle", name="Disk eject toggle", command="DISK_EJECT_TOGGLE"),
    RetroArchButtonDescription(key="disk_next", name="Disk next", command="DISK_NEXT"),
    RetroArchButtonDescription(key="disk_prev", name="Disk previous", command="DISK_PREV"),
    RetroArchButtonDescription(key="shader_next", name="Shader next", command="SHADER_NEXT"),
    RetroArchButtonDescription(key="shader_prev", name="Shader previous", command="SHADER_PREV"),
    RetroArchButtonDescription(key="shader_toggle", name="Shader toggle", command="SHADER_TOGGLE"),
    RetroArchButtonDescription(key="cheat_toggle", name="Cheat toggle", command="CHEAT_TOGGLE"),
    RetroArchButtonDescription(key="cheat_index_plus", name="Cheat index +", command="CHEAT_INDEX_PLUS"),
    RetroArchButtonDescription(key="cheat_index_minus", name="Cheat index -", command="CHEAT_INDEX_MINUS"),
    RetroArchButtonDescription(key="volume_up", name="Volume up", command="VOLUME_UP"),
    RetroArchButtonDescription(key="volume_down", name="Volume down", command="VOLUME_DOWN"),
    RetroArchButtonDescription(key="recording_toggle", name="Recording toggle", command="RECORDING_TOGGLE"),
    RetroArchButtonDescription(key="streaming_toggle", name="Streaming toggle", command="STREAMING_TOGGLE"),
    RetroArchButtonDescription(key="fps_toggle", name="FPS display toggle", command="FPS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="statistics_toggle", name="Statistics toggle", command="STATISTICS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="game_focus_toggle", name="Game focus toggle", command="GAME_FOCUS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="grab_mouse_toggle", name="Grab mouse toggle", command="GRAB_MOUSE_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="runahead_toggle", name="Run-ahead toggle", command="RUNAHEAD_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="vrr_runloop_toggle", name="VRR runloop toggle", command="VRR_RUNLOOP_TOGGLE", entity_category=EntityCategory.CONFIG),
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
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    async def async_press(self) -> None:
        await self.coordinator.client.send_command(self.entity_description.command)
