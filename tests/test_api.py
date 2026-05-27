"""Tests for the RetroArch UDP client."""
from __future__ import annotations

import pytest

from custom_components.retroarch.api import (
    RetroArchClient,
    RetroArchProtocol,
    RetroArchStatus,
    parse_status,
)


def test_parse_status_playing():
    status = parse_status("GET_STATUS PLAYING super_nintendo,Super Mario World,crc32=A31BEAD4")
    assert status.state == "playing"
    assert status.system == "super_nintendo"
    assert status.game == "Super Mario World"
    assert status.crc32 == "A31BEAD4"


def test_parse_status_paused():
    status = parse_status("GET_STATUS PAUSED nes,Metroid,crc32=DEADBEEF")
    assert status.state == "paused"
    assert status.system == "nes"
    assert status.game == "Metroid"
    assert status.crc32 == "DEADBEEF"


def test_parse_status_contentless():
    status = parse_status("GET_STATUS CONTENTLESS")
    assert status.state == "contentless"
    assert status.system is None
    assert status.game is None
    assert status.crc32 is None


def test_parse_status_game_name_with_comma():
    status = parse_status("GET_STATUS PLAYING psx,Final Fantasy VII, Disc 1,crc32=0000FFFF")
    assert status.system == "psx"
    assert status.game == "Final Fantasy VII, Disc 1"
    assert status.crc32 == "0000FFFF"


def test_parse_status_garbage_returns_unknown():
    status = parse_status("")
    assert status.state == "unknown"
