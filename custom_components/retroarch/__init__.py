"""The RetroArch integration."""
from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant

from .api import RetroArchClient
from .const import (
    CONF_RAM_SENSORS,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]


async def async_setup_entry(hass: HomeAssistant, entry: RetroArchConfigEntry) -> bool:
    """Set up RetroArch from a config entry."""
    client = RetroArchClient(entry.data[CONF_HOST], entry.data[CONF_PORT])

    coordinator = RetroArchDataUpdateCoordinator(
        hass,
        client=client,
        name=entry.data.get(CONF_NAME, DEFAULT_NAME),
        scan_interval=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ram_sensors=entry.options.get(CONF_RAM_SENSORS, []),
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Imported here (not at module top) so the package stays importable during
    # incremental development before services.py exists; it always ships in releases.
    from .services import async_setup_services

    async_setup_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RetroArchConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.client.close()
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: RetroArchConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
