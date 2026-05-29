"""Constants for the RetroArch integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "retroarch"

DEFAULT_NAME: Final = "RetroArch"
DEFAULT_PORT: Final = 55355
DEFAULT_SCAN_INTERVAL: Final = 5
DEFAULT_TIMEOUT: Final = 1.0

# Manufacturer string for the HA device registry.
MANUFACTURER: Final = "libretro"

# --- Status / info commands ---
CMD_GET_CONFIG_PARAM: Final = "GET_CONFIG_PARAM"
CMD_VERSION: Final = "VERSION"
CMD_GET_STATUS: Final = "GET_STATUS"
# --- Memory commands ---
CMD_READ_CORE_RAM: Final = "READ_CORE_RAM"
CMD_WRITE_CORE_RAM: Final = "WRITE_CORE_RAM"
# System-memory-map variants (work on more cores than CORE_RAM).
CMD_READ_CORE_MEMORY: Final = "READ_CORE_MEMORY"
CMD_WRITE_CORE_MEMORY: Final = "WRITE_CORE_MEMORY"

# --- Control commands with one argument ---
CMD_LOAD_STATE_SLOT: Final = "LOAD_STATE_SLOT"
CMD_PLAY_REPLAY_SLOT: Final = "PLAY_REPLAY_SLOT"
CMD_SHOW_MSG: Final = "SHOW_MSG"
CMD_SET_SHADER: Final = "SET_SHADER"
CMD_LOAD_CORE: Final = "LOAD_CORE"
CMD_SAVE_FILES: Final = "SAVE_FILES"
CMD_LOAD_FILES: Final = "LOAD_FILES"

# --- GitHub release feed for the update entity ---
GITHUB_LATEST_RELEASE_URL: Final = (
    "https://api.github.com/repos/libretro/RetroArch/releases/latest"
)

# --- Event bus events fired on game transitions ---
EVENT_GAME_STARTED: Final = "retroarch_game_started"
EVENT_GAME_STOPPED: Final = "retroarch_game_stopped"
EVENT_GAME_CHANGED: Final = "retroarch_game_changed"

# --- States reported by GET_STATUS ---
STATE_PLAYING: Final = "playing"
STATE_PAUSED: Final = "paused"
STATE_CONTENTLESS: Final = "contentless"
STATE_UNKNOWN: Final = "unknown"

# --- Options flow keys (RAM sensors) ---
CONF_RAM_SENSORS: Final = "ram_sensors"
CONF_RAM_NAME: Final = "name"
CONF_RAM_ADDRESS: Final = "address"   # hex string, e.g. "7e0019"
CONF_RAM_SIZE: Final = "size"         # number of bytes
CONF_RAM_SIGNED: Final = "signed"
CONF_RAM_BIG_ENDIAN: Final = "big_endian"
CONF_RAM_SCALE: Final = "scale"
CONF_RAM_UNIT: Final = "unit"
CONF_RAM_MEMORY_MAP: Final = "memory_map"  # use READ_CORE_MEMORY instead of READ_CORE_RAM

# --- Options flow keys (box art) ---
CONF_BOX_ART_ENABLED: Final = "box_art_enabled"
CONF_BOX_ART_SYSTEM: Final = "box_art_system"
