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


class FakeTransport:
    """Minimal asyncio.DatagramTransport stand-in for tests."""

    def __init__(self, protocol: RetroArchProtocol, response: bytes | None = None) -> None:
        self.protocol = protocol
        self.response = response
        self.sent: list[bytes] = []
        self._closing = False

    def is_closing(self) -> bool:
        return self._closing

    def sendto(self, data: bytes, addr=None) -> None:
        self.sent.append(data)
        if self.response is not None:
            # Simulate RetroArch replying on the same socket.
            self.protocol.datagram_received(self.response, ("127.0.0.1", 55355))

    def close(self) -> None:
        self._closing = True


def _wire_client(response: bytes | None) -> tuple[RetroArchClient, FakeTransport]:
    client = RetroArchClient("127.0.0.1", 55355, timeout=0.5)
    protocol = RetroArchProtocol()
    transport = FakeTransport(protocol, response)
    protocol.connection_made(transport)
    client._transport = transport
    client._protocol = protocol
    return client, transport


async def test_query_returns_decoded_response():
    client, _ = _wire_client(b"VERSION 1.19.1")
    assert await client.query("VERSION") == "VERSION 1.19.1"


async def test_query_times_out_when_no_response():
    client, _ = _wire_client(None)
    assert await client.query("VERSION") is None


async def test_send_command_is_fire_and_forget():
    client, transport = _wire_client(None)
    await client.send_command("RESET")
    assert transport.sent == [b"RESET"]


async def test_get_version_strips_prefix():
    client, _ = _wire_client(b"VERSION 1.19.1")
    assert await client.async_get_version() == "1.19.1"


async def test_get_status_sets_available():
    client, _ = _wire_client(b"GET_STATUS PLAYING nes,Metroid,crc32=DEADBEEF")
    status = await client.async_get_status()
    assert status.available is True
    assert status.game == "Metroid"


async def test_get_status_unavailable_on_timeout():
    client, _ = _wire_client(None)
    status = await client.async_get_status()
    assert status.available is False
    assert status.state == "unknown"


async def test_read_memory_parses_hex_bytes():
    client, transport = _wire_client(b"READ_CORE_RAM 7e0019 0a 14")
    assert await client.async_read_memory(0x7E0019, 2) == [0x0A, 0x14]
    assert transport.sent == [b"READ_CORE_RAM 7e0019 2"]


async def test_read_memory_returns_none_on_error():
    client, _ = _wire_client(b"READ_CORE_RAM 7e0019 -1")
    assert await client.async_read_memory(0x7E0019, 2) is None


async def test_write_memory_encodes_bytes():
    client, transport = _wire_client(None)
    await client.async_write_memory(0x7E0019, [0x0A, 0xFF])
    assert transport.sent == [b"WRITE_CORE_RAM 7e0019 a ff"]
