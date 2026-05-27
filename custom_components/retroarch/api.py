"""Async UDP client for the RetroArch Network Control Interface."""
from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass, field

from .const import (
    CMD_GET_STATUS,
    CMD_READ_CORE_RAM,
    CMD_VERSION,
    CMD_WRITE_CORE_RAM,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    STATE_CONTENTLESS,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

_STATE_MAP = {
    "PLAYING": STATE_PLAYING,
    "PAUSED": STATE_PAUSED,
    "CONTENTLESS": STATE_CONTENTLESS,
}


@dataclass
class RetroArchStatus:
    """Snapshot of a RetroArch instance."""

    available: bool = False
    state: str = STATE_UNKNOWN
    system: str | None = None
    game: str | None = None
    crc32: str | None = None
    version: str | None = None
    ram: dict[str, list[int]] = field(default_factory=dict)


def parse_status(response: str | None) -> RetroArchStatus:
    """Parse a GET_STATUS response into a RetroArchStatus (available is set by caller)."""
    if not response:
        return RetroArchStatus(state=STATE_UNKNOWN)

    payload = response.strip()
    if payload.startswith(CMD_GET_STATUS):
        payload = payload[len(CMD_GET_STATUS):].strip()

    if not payload:
        return RetroArchStatus(state=STATE_UNKNOWN)

    raw_state, _, info = payload.partition(" ")
    state = _STATE_MAP.get(raw_state.upper(), STATE_UNKNOWN)

    if state in (STATE_CONTENTLESS, STATE_UNKNOWN) or not info:
        return RetroArchStatus(state=state)

    crc32: str | None = None
    if ",crc32=" in info:
        info, _, crc32 = info.rpartition(",crc32=")

    system, _, game = info.partition(",")
    return RetroArchStatus(
        state=state,
        system=system or None,
        game=game or None,
        crc32=crc32 or None,
    )


class RetroArchProtocol(asyncio.DatagramProtocol):
    """Datagram protocol that resolves a future on the next inbound packet."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self.response_future: asyncio.Future[str] | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        if self.response_future is not None and not self.response_future.done():
            self.response_future.set_result(data.decode("utf-8", errors="replace").strip())

    def error_received(self, exc: Exception) -> None:
        if self.response_future is not None and not self.response_future.done():
            self.response_future.set_exception(exc)


class RetroArchClient:
    """Talks to one RetroArch instance over UDP."""

    def __init__(self, host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._lock = asyncio.Lock()
        self._transport: asyncio.DatagramTransport | None = None
        self._protocol: RetroArchProtocol | None = None

    async def _ensure_connection(self) -> None:
        if self._transport is None or self._transport.is_closing():
            loop = asyncio.get_running_loop()
            self._transport, self._protocol = await loop.create_datagram_endpoint(
                RetroArchProtocol,
                remote_addr=(self._host, self._port),
            )

    async def send_command(self, command: str) -> None:
        """Send a fire-and-forget command (no response expected)."""
        async with self._lock:
            await self._ensure_connection()
            assert self._transport is not None
            self._transport.sendto(command.encode("utf-8"))

    async def query(self, command: str) -> str | None:
        """Send a command and wait for a single UDP response. None on timeout."""
        async with self._lock:
            await self._ensure_connection()
            assert self._transport is not None and self._protocol is not None
            loop = asyncio.get_running_loop()
            self._protocol.response_future = loop.create_future()
            self._transport.sendto(command.encode("utf-8"))
            try:
                return await asyncio.wait_for(self._protocol.response_future, self._timeout)
            except asyncio.TimeoutError:
                return None
            except OSError as err:
                _LOGGER.debug("UDP error querying %s: %s", command, err)
                return None
            finally:
                self._protocol.response_future = None

    async def async_get_version(self) -> str | None:
        """Return the RetroArch version string, or None if unreachable."""
        response = await self.query(CMD_VERSION)
        if not response:
            return None
        # Response is either bare "1.19.1" or "VERSION 1.19.1".
        return response.replace(CMD_VERSION, "").strip() or None

    async def async_get_status(self) -> RetroArchStatus:
        """Poll GET_STATUS. available reflects whether a response arrived."""
        response = await self.query(CMD_GET_STATUS)
        status = parse_status(response)
        status.available = response is not None
        return status

    async def async_read_memory(self, address: int, size: int) -> list[int] | None:
        """Read `size` bytes from core RAM at `address`. None if unsupported/timeout."""
        response = await self.query(f"{CMD_READ_CORE_RAM} {address:x} {size}")
        if not response:
            return None
        tokens = response.split()
        # Expect: READ_CORE_RAM <addr> <b0> <b1> ...
        if len(tokens) < 3 or tokens[0] != CMD_READ_CORE_RAM:
            return None
        byte_tokens = tokens[2:]
        if byte_tokens == ["-1"]:
            return None
        try:
            return [int(token, 16) for token in byte_tokens]
        except ValueError:
            return None

    async def async_write_memory(self, address: int, data: list[int]) -> None:
        """Write bytes to core RAM at `address` (fire-and-forget)."""
        payload = " ".join(f"{byte & 0xFF:x}" for byte in data)
        await self.send_command(f"{CMD_WRITE_CORE_RAM} {address:x} {payload}")

    def close(self) -> None:
        """Close the UDP transport."""
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._protocol = None


async def async_discover(
    broadcast_addresses: list[str] | None = None,
    port: int = DEFAULT_PORT,
    timeout: float = 2.0,
) -> dict[str, str]:
    """Broadcast VERSION across the LAN and return {host: version} of responders."""
    targets = broadcast_addresses or ["255.255.255.255"]
    loop = asyncio.get_running_loop()
    responders: dict[str, str] = {}

    class _DiscoveryProtocol(asyncio.DatagramProtocol):
        def datagram_received(self, data: bytes, addr: tuple) -> None:
            version = data.decode("utf-8", errors="replace").replace(CMD_VERSION, "").strip()
            responders[addr[0]] = version or "unknown"

    transport, _ = await loop.create_datagram_endpoint(
        _DiscoveryProtocol,
        family=socket.AF_INET,
        allow_broadcast=True,
    )
    try:
        for address in targets:
            transport.sendto(CMD_VERSION.encode("utf-8"), (address, port))
        await asyncio.sleep(timeout)
    finally:
        transport.close()
    return responders
