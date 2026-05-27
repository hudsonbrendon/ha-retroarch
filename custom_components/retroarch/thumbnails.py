"""Best-effort libretro box-art URL construction.

GET_STATUS only gives a short system id and the ROM basename, while the
libretro thumbnail server is keyed by full system folder + playlist label.
Matching is therefore best-effort; users can override the system folder
(or disable box art) via the options flow.
"""
from __future__ import annotations

from urllib.parse import quote

THUMBNAIL_BASE = "https://thumbnails.libretro.com"

# Map GET_STATUS system ids -> libretro thumbnail folder names.
SYSTEM_FOLDERS: dict[str, str] = {
    "nintendo_entertainment_system": "Nintendo - Nintendo Entertainment System",
    "nes": "Nintendo - Nintendo Entertainment System",
    "super_nintendo": "Nintendo - Super Nintendo Entertainment System",
    "snes": "Nintendo - Super Nintendo Entertainment System",
    "nintendo_64": "Nintendo - Nintendo 64",
    "n64": "Nintendo - Nintendo 64",
    "game_boy": "Nintendo - Game Boy",
    "game_boy_color": "Nintendo - Game Boy Color",
    "game_boy_advance": "Nintendo - Game Boy Advance",
    "gba": "Nintendo - Game Boy Advance",
    "nintendo_ds": "Nintendo - Nintendo DS",
    "nintendo_gamecube": "Nintendo - GameCube",
    "sega_master_system": "Sega - Master System - Mark III",
    "sega_genesis": "Sega - Mega Drive - Genesis",
    "sega_mega_drive": "Sega - Mega Drive - Genesis",
    "genesis": "Sega - Mega Drive - Genesis",
    "sega_saturn": "Sega - Saturn",
    "sega_dreamcast": "Sega - Dreamcast",
    "sega_game_gear": "Sega - Game Gear",
    "playstation": "Sony - PlayStation",
    "psx": "Sony - PlayStation",
    "playstation_portable": "Sony - PlayStation Portable",
    "psp": "Sony - PlayStation Portable",
    "pc_engine": "NEC - PC Engine - TurboGrafx 16",
    "turbografx_16": "NEC - PC Engine - TurboGrafx 16",
    "atari_2600": "Atari - 2600",
    "atari_7800": "Atari - 7800",
    "neo_geo_pocket": "SNK - Neo Geo Pocket",
    "neo_geo_pocket_color": "SNK - Neo Geo Pocket Color",
    "wonderswan": "Bandai - WonderSwan",
    "wonderswan_color": "Bandai - WonderSwan Color",
    "msx": "Microsoft - MSX",
}

# Characters libretro replaces with "_" in thumbnail file names.
_SPECIAL = "&*/:`<>?\\|"
_TRANSLATION = {ord(ch): "_" for ch in _SPECIAL}


def sanitize(name: str) -> str:
    """Replace libretro-reserved characters with underscores."""
    return name.translate(_TRANSLATION)


def system_folder(system_id: str | None) -> str | None:
    """Map a GET_STATUS system id to a libretro thumbnail folder, or None."""
    if not system_id:
        return None
    return SYSTEM_FOLDERS.get(system_id.lower())


def boxart_url(
    system_id: str | None, game: str | None, override_folder: str | None
) -> str | None:
    """Build the Named_Boxarts URL, or None if system/game can't be resolved."""
    if not game:
        return None
    folder = override_folder or system_folder(system_id)
    if not folder:
        return None
    return f"{THUMBNAIL_BASE}/{quote(folder)}/Named_Boxarts/{quote(sanitize(game))}.png"
