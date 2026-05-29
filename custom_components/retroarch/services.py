"""Services for the RetroArch integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    CMD_LOAD_CORE,
    CMD_LOAD_FILES,
    CMD_LOAD_STATE_SLOT,
    CMD_PLAY_REPLAY_SLOT,
    CMD_SAVE_FILES,
    CMD_SET_SHADER,
    CMD_SHOW_MSG,
    DOMAIN,
)

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_COMMAND = "command"
ATTR_ADDRESS = "address"
ATTR_SIZE = "size"
ATTR_DATA = "data"
ATTR_MESSAGE = "message"
ATTR_SLOT = "slot"
ATTR_PATH = "path"

SERVICE_SEND_COMMAND = "send_command"
SERVICE_READ_MEMORY = "read_memory"
SERVICE_WRITE_MEMORY = "write_memory"
SERVICE_READ_MEMORY_MAP = "read_memory_map"
SERVICE_WRITE_MEMORY_MAP = "write_memory_map"
SERVICE_SHOW_MESSAGE = "show_message"
SERVICE_LOAD_STATE_SLOT = "load_state_slot"
SERVICE_PLAY_REPLAY_SLOT = "play_replay_slot"
SERVICE_SET_SHADER = "set_shader"
SERVICE_LOAD_CORE = "load_core"
SERVICE_SAVE_FILES = "save_files"
SERVICE_LOAD_FILES = "load_files"

_ENTRY = {vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string}

SEND_COMMAND_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_COMMAND): cv.string})
READ_MEMORY_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Required(ATTR_ADDRESS): cv.string, vol.Required(ATTR_SIZE): vol.All(int, vol.Range(min=1, max=256))}
)
WRITE_MEMORY_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Required(ATTR_ADDRESS): cv.string, vol.Required(ATTR_DATA): [vol.All(int, vol.Range(min=0, max=255))]}
)
SHOW_MESSAGE_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_MESSAGE): cv.string})
SLOT_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_SLOT): vol.All(int, vol.Range(min=0))})
LOAD_STATE_SLOT_SCHEMA = SLOT_SCHEMA
PLAY_REPLAY_SLOT_SCHEMA = SLOT_SCHEMA
SET_SHADER_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_PATH): cv.string})
LOAD_CORE_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_PATH): cv.string})
ENTRY_ONLY_SCHEMA = vol.Schema(_ENTRY)


def _get_coordinator(hass: HomeAssistant, call: ServiceCall):
    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(f"RetroArch config entry {entry_id} not found or not loaded")
    return entry.runtime_data


def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""

    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    async def handle_send_command(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(call.data[ATTR_COMMAND])

    async def handle_read_memory(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        address = int(call.data[ATTR_ADDRESS], 16)
        values = await coordinator.client.async_read_memory(address, call.data[ATTR_SIZE])
        if values is None:
            return {"data": [], "hex": "", "error": "unsupported or no response"}
        return {"data": values, "hex": " ".join(f"{b:02x}" for b in values)}

    async def handle_write_memory(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        address = int(call.data[ATTR_ADDRESS], 16)
        await coordinator.client.async_write_memory(address, list(call.data[ATTR_DATA]))

    async def handle_read_memory_map(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        address = int(call.data[ATTR_ADDRESS], 16)
        values = await coordinator.client.async_read_memory_map(address, call.data[ATTR_SIZE])
        if values is None:
            return {"data": [], "hex": "", "error": "unsupported or no response"}
        return {"data": values, "hex": " ".join(f"{b:02x}" for b in values)}

    async def handle_write_memory_map(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        address = int(call.data[ATTR_ADDRESS], 16)
        await coordinator.client.async_write_memory_map(address, list(call.data[ATTR_DATA]))

    async def handle_save_files(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(CMD_SAVE_FILES)

    async def handle_load_files(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(CMD_LOAD_FILES)

    async def handle_play_replay_slot(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"{CMD_PLAY_REPLAY_SLOT} {call.data[ATTR_SLOT]}")

    async def handle_show_message(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"{CMD_SHOW_MSG} {call.data[ATTR_MESSAGE]}")

    async def handle_load_state_slot(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"{CMD_LOAD_STATE_SLOT} {call.data[ATTR_SLOT]}")

    async def handle_set_shader(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"{CMD_SET_SHADER} {call.data[ATTR_PATH]}")

    async def handle_load_core(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"{CMD_LOAD_CORE} {call.data[ATTR_PATH]}")

    hass.services.async_register(DOMAIN, SERVICE_SEND_COMMAND, handle_send_command, schema=SEND_COMMAND_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_READ_MEMORY, handle_read_memory, schema=READ_MEMORY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, SERVICE_WRITE_MEMORY, handle_write_memory, schema=WRITE_MEMORY_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_READ_MEMORY_MAP, handle_read_memory_map, schema=READ_MEMORY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, SERVICE_WRITE_MEMORY_MAP, handle_write_memory_map, schema=WRITE_MEMORY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SHOW_MESSAGE, handle_show_message, schema=SHOW_MESSAGE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_LOAD_STATE_SLOT, handle_load_state_slot, schema=LOAD_STATE_SLOT_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PLAY_REPLAY_SLOT, handle_play_replay_slot, schema=PLAY_REPLAY_SLOT_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_SHADER, handle_set_shader, schema=SET_SHADER_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_LOAD_CORE, handle_load_core, schema=LOAD_CORE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SAVE_FILES, handle_save_files, schema=ENTRY_ONLY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_LOAD_FILES, handle_load_files, schema=ENTRY_ONLY_SCHEMA)
