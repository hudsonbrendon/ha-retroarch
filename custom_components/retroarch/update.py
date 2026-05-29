"""Update platform: compares the running RetroArch version with the latest release."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import GITHUB_LATEST_RELEASE_URL
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity

_LOGGER = logging.getLogger(__name__)
_REFRESH_INTERVAL = timedelta(hours=12)
RELEASE_PAGE = "https://github.com/libretro/RetroArch/releases/latest"


async def async_fetch_latest_version(hass: HomeAssistant) -> str | None:
    """Return the latest RetroArch release version (tag without a leading 'v')."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(GITHUB_LATEST_RELEASE_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            payload = await resp.json()
    except Exception as err:  # noqa: BLE001  # best-effort; never crash the entity
        _LOGGER.debug("Could not fetch latest RetroArch release: %s", err)
        return None
    tag = payload.get("tag_name") or payload.get("name")
    if not tag:
        return None
    return str(tag).lstrip("vV").strip() or None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RetroArchUpdate(entry.runtime_data)])


class RetroArchUpdate(RetroArchEntity, UpdateEntity):
    """Shows whether a newer RetroArch release is available (informational only)."""

    _attr_translation_key = "retroarch"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_supported_features = UpdateEntityFeature.RELEASE_NOTES
    _attr_release_url = RELEASE_PAGE
    _attr_title = "RetroArch"

    def __init__(self, coordinator: RetroArchDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_update"
        self._latest: str | None = None

    @property
    def installed_version(self) -> str | None:
        return self.coordinator.data.version

    @property
    def latest_version(self) -> str | None:
        # Fall back to the installed version so HA doesn't flag a phantom update
        # before the first successful fetch.
        return self._latest or self.coordinator.data.version

    async def async_release_notes(self) -> str | None:
        return f"See the [RetroArch release notes]({RELEASE_PAGE})."

    async def _async_refresh_latest(self, _now=None) -> None:
        latest = await async_fetch_latest_version(self.hass)
        if latest is not None and latest != self._latest:
            self._latest = latest
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Fetch off the setup path so a slow/unreachable GitHub never blocks startup.
        self.hass.async_create_background_task(
            self._async_refresh_latest(), name="retroarch_update_check"
        )
        self.async_on_remove(
            async_track_time_interval(self.hass, self._async_refresh_latest, _REFRESH_INTERVAL)
        )
