"""DataUpdateCoordinator for the RetroArch integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import RetroArchClient, RetroArchStatus
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type RetroArchConfigEntry = ConfigEntry["RetroArchDataUpdateCoordinator"]

CONFIG_PARAMS: tuple[str, ...] = ("video_driver", "audio_driver", "menu_driver")


class RetroArchDataUpdateCoordinator(DataUpdateCoordinator[RetroArchStatus]):
    """Polls one RetroArch instance and shares a RetroArchStatus snapshot."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: RetroArchClient,
        name: str,
        scan_interval: int,
        ram_sensors: list[dict],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {name}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.device_name = name
        self.ram_sensors = ram_sensors
        self._version: str | None = None
        self._config: dict[str, str] | None = None

    async def _async_update_data(self) -> RetroArchStatus:
        status = await self.client.async_get_status()

        if not status.available:
            return status

        # Version rarely changes; fetch once and cache.
        if self._version is None:
            self._version = await self.client.async_get_version()
        status.version = self._version

        if self._config is None:
            self._config = {}
            for param in CONFIG_PARAMS:
                value = await self.client.async_get_config_param(param)
                if value is not None:
                    self._config[param] = value
        status.config = self._config

        for sensor in self.ram_sensors:
            address = int(str(sensor["address"]), 16)
            size = int(sensor["size"])
            value = await self.client.async_read_memory(address, size)
            if value is not None:
                status.ram[sensor["name"]] = value

        return status
