"""Tests for the RetroArch update entity."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN
from custom_components.retroarch.update import async_fetch_latest_version

from .const import MOCK_CONFIG


class _FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def __init__(self, response):
        self._response = response

    def get(self, url, timeout=None):
        return self._response


def _patch_session(response):
    return patch(
        "custom_components.retroarch.update.async_get_clientsession",
        return_value=_FakeSession(response),
    )


async def test_fetch_latest_version_strips_v(hass):
    with _patch_session(_FakeResponse(200, {"tag_name": "v1.20.0"})):
        assert await async_fetch_latest_version(hass) == "1.20.0"


async def test_fetch_latest_version_handles_error(hass):
    with _patch_session(_FakeResponse(500, {})):
        assert await async_fetch_latest_version(hass) is None


async def test_update_entity_reports_available_release(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    status = RetroArchStatus(available=True, state="playing", game="X", version="1.19.1")
    with patch("custom_components.retroarch.PLATFORMS", [Platform.UPDATE]), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=AsyncMock(return_value=None),
    ), patch(
        "custom_components.retroarch.update.async_fetch_latest_version",
        new=AsyncMock(return_value="1.20.0"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("update.retroarch_retroarch")
    assert state.attributes["installed_version"] == "1.19.1"
    assert state.attributes["latest_version"] == "1.20.0"
    assert state.state == "on"  # update available
