"""Diagnostics support for RetroArch."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import RetroArchConfigEntry

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RetroArchConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "status": {
            "available": data.available,
            "state": data.state,
            "system": data.system,
            "game": data.game,
            "crc32": data.crc32,
            "version": data.version,
            "config": data.config,
            "ram_keys": list(data.ram),
        },
    }
