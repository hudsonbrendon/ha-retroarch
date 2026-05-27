"""Base entity for the RetroArch integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import RetroArchDataUpdateCoordinator


class RetroArchEntity(CoordinatorEntity[RetroArchDataUpdateCoordinator]):
    """Common device info + availability for RetroArch entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RetroArchDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model="RetroArch",
            sw_version=coordinator.data.version if coordinator.data else None,
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.available
