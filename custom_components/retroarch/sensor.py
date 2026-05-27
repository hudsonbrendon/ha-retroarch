"""Sensor platform for RetroArch."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import RetroArchStatus
from .const import (
    CONF_RAM_ADDRESS,
    CONF_RAM_BIG_ENDIAN,
    CONF_RAM_NAME,
    CONF_RAM_SCALE,
    CONF_RAM_SENSORS,
    CONF_RAM_SIGNED,
    CONF_RAM_UNIT,
)
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchSensorDescription(SensorEntityDescription):
    """Describes a status sensor."""

    value_fn: Callable[[RetroArchStatus], StateType]


STATUS_SENSORS: tuple[RetroArchSensorDescription, ...] = (
    RetroArchSensorDescription(
        key="status",
        value_fn=lambda data: data.state,
    ),
    RetroArchSensorDescription(
        key="game",
        value_fn=lambda data: data.game,
    ),
    RetroArchSensorDescription(
        key="system",
        value_fn=lambda data: data.system,
    ),
    RetroArchSensorDescription(
        key="crc32",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.crc32,
    ),
    RetroArchSensorDescription(
        key="version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.version,
    ),
)


CONFIG_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(key="netplay_nickname", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    SensorEntityDescription(key="savefile_directory", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    SensorEntityDescription(key="savestate_directory", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    SensorEntityDescription(key="system_directory", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    SensorEntityDescription(key="cache_directory", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    SensorEntityDescription(key="log_dir", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    SensorEntityDescription(key="runtime_log_directory", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RetroArch sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        RetroArchSensor(coordinator, description) for description in STATUS_SENSORS
    ]
    for ram in entry.options.get(CONF_RAM_SENSORS, []):
        entities.append(RetroArchRamSensor(coordinator, ram))
    entities.extend(
        RetroArchConfigSensor(coordinator, description) for description in CONFIG_SENSORS
    )
    async_add_entities(entities)


def _decode(values: list[int], *, signed: bool, big_endian: bool, scale: float) -> float | int:
    raw = int.from_bytes(
        bytes(b & 0xFF for b in values),
        byteorder="big" if big_endian else "little",
        signed=signed,
    )
    result = raw * scale
    return int(result) if scale == 1.0 else result


class RetroArchSensor(RetroArchEntity, SensorEntity):
    """A status sensor backed by the coordinator snapshot."""

    entity_description: RetroArchSensorDescription

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)


class RetroArchConfigSensor(RetroArchEntity, SensorEntity):
    """A diagnostic sensor reading a cached retroarch.cfg parameter."""

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_cfg_{description.key}"

    @property
    def native_value(self) -> StateType:
        return self.coordinator.data.config.get(self.entity_description.key)


class RetroArchRamSensor(RetroArchEntity, SensorEntity):
    """A user-configured sensor reading a value from core RAM."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: RetroArchDataUpdateCoordinator, config: dict
    ) -> None:
        super().__init__(coordinator)
        self._config = config
        name = config[CONF_RAM_NAME]
        self._attr_name = name
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_ram_{config[CONF_RAM_ADDRESS]}_{name}"
        )
        unit = config.get(CONF_RAM_UNIT) or None
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> StateType:
        values = self.coordinator.data.ram.get(self._config[CONF_RAM_NAME])
        if not values:
            return None
        return _decode(
            values,
            signed=self._config.get(CONF_RAM_SIGNED, False),
            big_endian=self._config.get(CONF_RAM_BIG_ENDIAN, False),
            scale=float(self._config.get(CONF_RAM_SCALE, 1.0)),
        )
