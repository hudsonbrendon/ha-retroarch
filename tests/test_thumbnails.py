"""Tests for the libretro thumbnail URL helper."""
from custom_components.retroarch.thumbnails import boxart_url, sanitize, system_folder


def test_sanitize_replaces_special_chars():
    assert sanitize("Pokémon: Red & Blue / X*?") == "Pokémon_ Red _ Blue _ X__"


def test_system_folder_known():
    assert system_folder("super_nintendo") == "Nintendo - Super Nintendo Entertainment System"


def test_system_folder_unknown_returns_none():
    assert system_folder("totally_made_up") is None


def test_boxart_url_known_system():
    url = boxart_url("super_nintendo", "Super Mario World (USA)", None)
    assert url == (
        "https://thumbnails.libretro.com/"
        "Nintendo%20-%20Super%20Nintendo%20Entertainment%20System/"
        "Named_Boxarts/Super%20Mario%20World%20%28USA%29.png"
    )


def test_boxart_url_override_system():
    url = boxart_url("whatever", "Game", "Sega - Mega Drive - Genesis")
    assert url.startswith(
        "https://thumbnails.libretro.com/Sega%20-%20Mega%20Drive%20-%20Genesis/Named_Boxarts/"
    )


def test_boxart_url_unknown_no_override_returns_none():
    assert boxart_url("totally_made_up", "Game", None) is None


def test_boxart_url_requires_game():
    assert boxart_url("super_nintendo", None, None) is None
