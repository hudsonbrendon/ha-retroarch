"""Number platform for RetroArch (save-state slot selector)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity

# RetroArch exposes no "set slot" command — only STATE_SLOT_PLUS / STATE_SLOT_MINUS.
# We read the current slot from the state_slot config param and step to the target.
_MAX_STEPS = 999


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RetroArchStateSlotNumber(entry.runtime_data)])


class RetroArchStateSlotNumber(RetroArchEntity, NumberEntity):
    """Selects the active save-state slot by stepping plus/minus to the target."""

    _attr_translation_key = "state_slot"
    _attr_native_min_value = 0
    _attr_native_max_value = _MAX_STEPS
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: RetroArchDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_state_slot"

    @property
    def native_value(self) -> float | None:
        raw = self.coordinator.data.config.get("state_slot")
        if raw is None:
            return None
        try:
            return float(int(raw))
        except ValueError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        current = self.native_value
        target = int(value)
        if current is None:
            return
        delta = target - int(current)
        if delta == 0:
            return
        command = "STATE_SLOT_PLUS" if delta > 0 else "STATE_SLOT_MINUS"
        for _ in range(min(abs(delta), _MAX_STEPS)):
            await self.coordinator.client.send_command(command)
        await self.coordinator.async_request_refresh()
