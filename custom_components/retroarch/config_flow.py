"""Config and options flow for the RetroArch integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.components import network
from homeassistant.core import callback

from .api import RetroArchClient, async_discover
from .const import (
    CONF_BOX_ART_ENABLED,
    CONF_BOX_ART_SYSTEM,
    CONF_RAM_ADDRESS,
    CONF_RAM_BIG_ENDIAN,
    CONF_RAM_NAME,
    CONF_RAM_SCALE,
    CONF_RAM_SENSORS,
    CONF_RAM_SIGNED,
    CONF_RAM_SIZE,
    CONF_RAM_UNIT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from homeassistant.const import CONF_SCAN_INTERVAL

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


class RetroArchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the RetroArch config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer automatic discovery or manual entry."""
        return self.async_show_menu(step_id="user", menu_options=["discover", "manual"])

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Scan the LAN and let the user pick a discovered instance."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            if await self._async_reachable(user_input):
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
            errors["base"] = "cannot_connect"
        else:
            self._discovered = await self._async_scan()
            if not self._discovered:
                # Nothing answered the broadcast — fall back to manual entry.
                return await self.async_step_manual()

        host_options = {
            ip: f"{ip} (v{version})" for ip, version in self._discovered.items()
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): vol.In(host_options),
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )
        return self.async_show_form(step_id="discover", data_schema=schema, errors=errors)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual host/port entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            if await self._async_reachable(user_input):
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual", data_schema=USER_SCHEMA, errors=errors
        )

    async def _async_reachable(self, user_input: dict[str, Any]) -> bool:
        client = RetroArchClient(user_input[CONF_HOST], user_input[CONF_PORT])
        try:
            return await client.async_get_version() is not None
        finally:
            client.close()

    async def _async_scan(self) -> dict[str, str]:
        addresses: list[str] | None = None
        try:
            broadcasts = await network.async_get_ipv4_broadcast_addresses(self.hass)
            addresses = [str(address) for address in broadcasts]
        except Exception:  # noqa: BLE001  # network helper may be unavailable
            addresses = None
        return await async_discover(addresses)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> RetroArchOptionsFlow:
        return RetroArchOptionsFlow()


class RetroArchOptionsFlow(OptionsFlow):
    """Options: polling interval + RAM sensor management."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "box_art", "add_ram_sensor", "remove_ram_sensor"],
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save({CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]})

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(int, vol.Range(min=1))}
        )
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_box_art(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(
                {
                    CONF_BOX_ART_ENABLED: user_input[CONF_BOX_ART_ENABLED],
                    CONF_BOX_ART_SYSTEM: user_input.get(CONF_BOX_ART_SYSTEM, ""),
                }
            )

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BOX_ART_ENABLED,
                    default=options.get(CONF_BOX_ART_ENABLED, True),
                ): bool,
                vol.Optional(
                    CONF_BOX_ART_SYSTEM,
                    default=options.get(CONF_BOX_ART_SYSTEM, ""),
                ): str,
            }
        )
        return self.async_show_form(step_id="box_art", data_schema=schema)

    async def async_step_add_ram_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            sensors = list(self.config_entry.options.get(CONF_RAM_SENSORS, []))
            sensors.append(
                {
                    CONF_RAM_NAME: user_input[CONF_RAM_NAME],
                    CONF_RAM_ADDRESS: user_input[CONF_RAM_ADDRESS],
                    CONF_RAM_SIZE: user_input[CONF_RAM_SIZE],
                    CONF_RAM_SIGNED: user_input.get(CONF_RAM_SIGNED, False),
                    CONF_RAM_BIG_ENDIAN: user_input.get(CONF_RAM_BIG_ENDIAN, False),
                    CONF_RAM_SCALE: user_input.get(CONF_RAM_SCALE, 1.0),
                    CONF_RAM_UNIT: user_input.get(CONF_RAM_UNIT, ""),
                }
            )
            return self._save({CONF_RAM_SENSORS: sensors})

        schema = vol.Schema(
            {
                vol.Required(CONF_RAM_NAME): str,
                vol.Required(CONF_RAM_ADDRESS): str,
                vol.Required(CONF_RAM_SIZE, default=1): vol.All(int, vol.Range(min=1, max=8)),
                vol.Optional(CONF_RAM_SIGNED, default=False): bool,
                vol.Optional(CONF_RAM_BIG_ENDIAN, default=False): bool,
                vol.Optional(CONF_RAM_SCALE, default=1.0): vol.Coerce(float),
                vol.Optional(CONF_RAM_UNIT, default=""): str,
            }
        )
        return self.async_show_form(step_id="add_ram_sensor", data_schema=schema)

    async def async_step_remove_ram_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        sensors = list(self.config_entry.options.get(CONF_RAM_SENSORS, []))
        names = [sensor[CONF_RAM_NAME] for sensor in sensors]

        if not names:
            return self.async_abort(reason="no_ram_sensors")

        if user_input is not None:
            remaining = [s for s in sensors if s[CONF_RAM_NAME] != user_input[CONF_RAM_NAME]]
            return self._save({CONF_RAM_SENSORS: remaining})

        schema = vol.Schema({vol.Required(CONF_RAM_NAME): vol.In(names)})
        return self.async_show_form(step_id="remove_ram_sensor", data_schema=schema)

    def _save(self, changes: dict[str, Any]) -> ConfigFlowResult:
        new_options = {**self.config_entry.options, **changes}
        return self.async_create_entry(title="", data=new_options)
