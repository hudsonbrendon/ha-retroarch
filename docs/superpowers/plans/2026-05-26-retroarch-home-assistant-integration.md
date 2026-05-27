# RetroArch Home Assistant Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS-distributable custom integration (`retroarch`) that talks to RetroArch's UDP Network Control Interface to expose the maximum possible set of sensors, binary sensors, a media_player, buttons, switches, services (including raw RAM read/write), and user-configurable RAM data sensors.

**Architecture:** A single async UDP client (`asyncio.DatagramProtocol`) drives all communication on port 55355. A `DataUpdateCoordinator` polls `GET_STATUS` (and configured RAM addresses) every few seconds and shares one `RetroArchStatus` snapshot. Every platform (sensor, binary_sensor, button, switch, media_player) reads from that coordinator; control commands are fire-and-forget UDP packets, RAM/status commands are request/response. Each config entry = one RetroArch instance = one HA device. RAM sensors are defined through an Options flow and reloaded on change. Setup supports both automatic LAN discovery (an active UDP `VERSION` broadcast probe — RetroArch has no mDNS/SSDP to discover passively) and manual host/port entry.

**Tech Stack:** Python 3.12+, Home Assistant (`homeassistant` core), `asyncio` UDP datagram endpoint (stdlib — no external runtime deps), `pytest` + `pytest-homeassistant-custom-component` for tests, HACS + GitHub Actions (hassfest + HACS validate) for distribution.

---

## RetroArch Network Control Interface — Reference

This is the protocol the integration speaks. Source: <https://docs.libretro.com/development/retroarch/network-control-interface/>.

**Setup (user side, documented in README):** in `retroarch.cfg` set `network_cmd_enable = "true"` and `network_cmd_port = "55355"`. Commands are UDP packets to `host:55355`. Commands that return data reply with a UDP packet back to the sender.

**Status / info (request → response):**
- `VERSION` → version string, e.g. `1.19.1`
- `GET_STATUS` → `GET_STATUS PLAYING system_id,game_basename,crc32=XXXXXXXX` / `GET_STATUS PAUSED ...` / `GET_STATUS CONTENTLESS`
- `GET_CONFIG_PARAM <name>` → `GET_CONFIG_PARAM <name> <value>`

**Memory (request → response):**
- `READ_CORE_RAM <addr-hex> <num-bytes>` → `READ_CORE_RAM <addr> <b0> <b1> ...` (hex bytes) or `READ_CORE_RAM <addr> -1` on failure
- `WRITE_CORE_RAM <addr-hex> <b0> <b1> ...` (hex bytes) → no response

**Control / hotkey (fire-and-forget, no args):**
`MENU_TOGGLE`, `QUIT`, `CLOSE_CONTENT`, `RESET`, `PAUSE_TOGGLE`, `FRAMEADVANCE`, `FAST_FORWARD`, `FAST_FORWARD_HOLD`, `SLOWMOTION`, `SLOWMOTION_HOLD`, `REWIND`, `MUTE`, `VOLUME_UP`, `VOLUME_DOWN`, `LOAD_STATE`, `SAVE_STATE`, `STATE_SLOT_PLUS`, `STATE_SLOT_MINUS`, `DISK_EJECT_TOGGLE`, `DISK_NEXT`, `DISK_PREV`, `SHADER_TOGGLE`, `SHADER_NEXT`, `SHADER_PREV`, `CHEAT_TOGGLE`, `CHEAT_INDEX_PLUS`, `CHEAT_INDEX_MINUS`, `SCREENSHOT`, `RECORDING_TOGGLE`, `STREAMING_TOGGLE`, `FULLSCREEN_TOGGLE`, `GAME_FOCUS_TOGGLE`, `GRAB_MOUSE_TOGGLE`, `FPS_TOGGLE`, `STATISTICS_TOGGLE`, `RUNAHEAD_TOGGLE`, `VRR_RUNLOOP_TOGGLE`, `AI_SERVICE`.

**Control (one arg):**
- `LOAD_STATE_SLOT <slot>`, `SHOW_MSG <text>`, `SET_SHADER <path>`, `LOAD_CORE <path>`

---

## File Structure

Repository root: `~/Github/ha-retroarch/`

```
ha-retroarch/
├── custom_components/
│   └── retroarch/
│       ├── __init__.py            # entry setup/unload, runtime_data, platform forward, service register
│       ├── const.py               # DOMAIN, defaults, command-string constants, option keys
│       ├── api.py                 # RetroArchProtocol, RetroArchClient, RetroArchStatus, parse_status
│       ├── coordinator.py         # RetroArchDataUpdateCoordinator + RetroArchConfigEntry type
│       ├── config_flow.py         # ConfigFlow + OptionsFlow (RAM sensors)
│       ├── entity.py              # RetroArchEntity base (device_info + availability)
│       ├── sensor.py              # status sensors + RAM sensors
│       ├── binary_sensor.py       # connectivity / playing / paused
│       ├── button.py              # all fire-and-forget control commands
│       ├── switch.py              # optimistic toggle switches
│       ├── media_player.py        # RetroArch as a media_player
│       ├── services.py            # send_command / read_memory / write_memory / show_message / load_state_slot / set_shader / load_core
│       ├── services.yaml          # service descriptions
│       ├── manifest.json
│       ├── strings.json
│       └── translations/
│           ├── en.json
│           └── pt-BR.json
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── const.py
│   ├── test_api.py
│   ├── test_coordinator.py
│   ├── test_config_flow.py
│   ├── test_init.py
│   ├── test_sensor.py
│   ├── test_binary_sensor.py
│   ├── test_button.py
│   ├── test_switch.py
│   ├── test_media_player.py
│   └── test_services.py
├── .github/workflows/
│   ├── validate.yaml              # hassfest + HACS action
│   └── tests.yaml                 # pytest
├── hacs.json
├── requirements_test.txt
├── README.md
└── LICENSE
```

**Responsibility split:** `api.py` knows the wire protocol and nothing about HA. `coordinator.py` owns polling cadence + the shared snapshot. Each platform file is purely a thin mapping from snapshot/commands to HA entities. `services.py` exposes power-user actions. This keeps every file small and independently testable.

---

## Task 1: Repository scaffold + dev environment

**Files:**
- Create: `~/Github/ha-retroarch/requirements_test.txt`
- Create: `~/Github/ha-retroarch/tests/__init__.py`
- Create: `~/Github/ha-retroarch/tests/conftest.py`
- Create: `~/Github/ha-retroarch/custom_components/retroarch/__init__.py` (placeholder, replaced in Task 7)
- Create: `~/Github/ha-retroarch/.gitignore`

- [ ] **Step 1: Create the repo and Python virtualenv**

```bash
mkdir -p ~/Github/ha-retroarch/custom_components/retroarch/translations
mkdir -p ~/Github/ha-retroarch/tests
mkdir -p ~/Github/ha-retroarch/.github/workflows
cd ~/Github/ha-retroarch
git init
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

- [ ] **Step 2: Write the test requirements file**

Create `requirements_test.txt`:

```text
homeassistant==2025.5.0
pytest-homeassistant-custom-component==0.13.230
pytest==8.3.5
pytest-asyncio==0.24.0
pytest-cov==6.1.1
```

> Note: `pytest-homeassistant-custom-component` pins a matching `homeassistant`. If pip reports a version conflict, drop the explicit `homeassistant` pin and let the plugin pull its matching core. Run `pip index versions pytest-homeassistant-custom-component` to pick the latest if 0.13.230 is unavailable.

- [ ] **Step 3: Install dependencies**

Run: `pip install -r requirements_test.txt`
Expected: installs Home Assistant core + test harness without error.

- [ ] **Step 4: Write `.gitignore`**

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
.DS_Store
```

- [ ] **Step 5: Write `tests/__init__.py`**

Create `tests/__init__.py`:

```python
"""Tests for the RetroArch integration."""
```

- [ ] **Step 6: Write `tests/conftest.py`**

Create `tests/conftest.py`:

```python
"""Fixtures for RetroArch tests."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield
```

- [ ] **Step 7: Write a temporary `__init__.py` so the component is importable**

Create `custom_components/retroarch/__init__.py`:

```python
"""The RetroArch integration."""
```

- [ ] **Step 8: Configure pytest**

Create `pytest.ini` at repo root:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 9: Verify the harness runs**

Run: `python -m pytest -q`
Expected: `no tests ran` (0 collected) with exit code 5, and no import/collection errors.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "chore: scaffold ha-retroarch repo and test harness"
```

---

## Task 2: Constants

**Files:**
- Create: `custom_components/retroarch/const.py`

- [ ] **Step 1: Write `const.py`**

Create `custom_components/retroarch/const.py`:

```python
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
CMD_VERSION: Final = "VERSION"
CMD_GET_STATUS: Final = "GET_STATUS"
CMD_GET_CONFIG_PARAM: Final = "GET_CONFIG_PARAM"

# --- Memory commands ---
CMD_READ_CORE_RAM: Final = "READ_CORE_RAM"
CMD_WRITE_CORE_RAM: Final = "WRITE_CORE_RAM"

# --- Control commands with one argument ---
CMD_LOAD_STATE_SLOT: Final = "LOAD_STATE_SLOT"
CMD_SHOW_MSG: Final = "SHOW_MSG"
CMD_SET_SHADER: Final = "SET_SHADER"
CMD_LOAD_CORE: Final = "LOAD_CORE"

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
```

- [ ] **Step 2: Commit**

```bash
git add custom_components/retroarch/const.py
git commit -m "feat: add integration constants"
```

---

## Task 3: UDP client — protocol, connection, status

**Files:**
- Create: `custom_components/retroarch/api.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test for `parse_status`**

Create `tests/test_api.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_api.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.retroarch.api'`

- [ ] **Step 3: Write `api.py` with `RetroArchStatus`, `parse_status`, `RetroArchProtocol`, `RetroArchClient`**

Create `custom_components/retroarch/api.py`:

```python
"""Async UDP client for the RetroArch Network Control Interface."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from .const import (
    CMD_GET_STATUS,
    CMD_READ_CORE_RAM,
    CMD_VERSION,
    CMD_WRITE_CORE_RAM,
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_api.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/api.py tests/test_api.py
git commit -m "feat: add UDP client and GET_STATUS parsing"
```

---

## Task 4: UDP client — query/command transport behavior + memory

**Files:**
- Modify: `tests/test_api.py` (append)

- [ ] **Step 1: Write failing tests for transport behavior using a fake transport**

Append to `tests/test_api.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails or passes**

Run: `python -m pytest tests/test_api.py -q`
Expected: all pass (the `api.py` from Task 3 already implements this behavior). If `test_query_times_out_when_no_response` hangs, confirm `timeout=0.5` is honored by `asyncio.wait_for`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api.py
git commit -m "test: cover UDP query/command transport and memory ops"
```

---

## Task 4b: LAN auto-discovery probe

RetroArch's command interface does **not** advertise over mDNS/zeroconf/SSDP, so Home Assistant's passive discovery cannot see it. The only viable automatic discovery is an active probe: broadcast `VERSION` to the LAN broadcast address(es) on port 55355 and collect the instances that reply.

**Files:**
- Modify: `custom_components/retroarch/api.py` (add `import socket` + `async_discover`)
- Modify: `tests/test_api.py` (append)

- [ ] **Step 1: Write the failing discovery test**

Append to `tests/test_api.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.retroarch import api as ra_api


async def test_async_discover_collects_responders():
    state: dict = {}

    class _FakeTransport:
        def sendto(self, data, addr=None):
            state["sent"] = (data, addr)

        def close(self):
            state["closed"] = True

    async def fake_endpoint(protocol_factory, family=None, allow_broadcast=None):
        protocol = protocol_factory()
        state["protocol"] = protocol
        return _FakeTransport(), protocol

    async def fake_sleep(_seconds):
        # Simulate a RetroArch instance replying during the wait window.
        state["protocol"].datagram_received(b"VERSION 1.19.1", ("192.168.1.50", 55355))

    fake_loop = MagicMock()
    fake_loop.create_datagram_endpoint = AsyncMock(side_effect=fake_endpoint)

    with patch.object(ra_api.asyncio, "get_running_loop", return_value=fake_loop), patch.object(
        ra_api.asyncio, "sleep", new=fake_sleep
    ):
        result = await ra_api.async_discover(["192.168.1.255"], timeout=0.01)

    assert result == {"192.168.1.50": "1.19.1"}
    assert state["closed"] is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_api.py::test_async_discover_collects_responders -q`
Expected: FAIL — `module 'custom_components.retroarch.api' has no attribute 'async_discover'`

- [ ] **Step 3: Add `import socket` and `async_discover` to `api.py`**

In `custom_components/retroarch/api.py`, add `import socket` to the imports (right after `import logging`), then append this function at module level (after the `RetroArchClient` class):

```python
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
```

> `DEFAULT_PORT` and `CMD_VERSION` are already imported at the top of `api.py` (Task 3). `allow_broadcast=True` sets `SO_BROADCAST` on the socket; sending to each interface's broadcast address means one packet reaches every RetroArch on that segment, and replies come back to our ephemeral source port.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_api.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/api.py tests/test_api.py
git commit -m "feat: add LAN broadcast discovery probe"
```

---

## Task 5: Data update coordinator

**Files:**
- Create: `custom_components/retroarch/coordinator.py`
- Test: `tests/test_coordinator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_coordinator.py`:

```python
"""Tests for the RetroArch coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.coordinator import RetroArchDataUpdateCoordinator


async def test_coordinator_merges_status_version_and_ram(hass):
    client = AsyncMock()
    client.async_get_status.return_value = RetroArchStatus(
        available=True, state="playing", system="nes", game="Metroid", crc32="DEADBEEF"
    )
    client.async_get_version.return_value = "1.19.1"
    client.async_read_memory.return_value = [0x0A]

    coordinator = RetroArchDataUpdateCoordinator(
        hass,
        client=client,
        name="RetroArch",
        scan_interval=5,
        ram_sensors=[{"name": "Lives", "address": "7e0019", "size": 1}],
    )

    data = await coordinator._async_update_data()

    assert data.available is True
    assert data.game == "Metroid"
    assert data.version == "1.19.1"
    assert data.ram["Lives"] == [0x0A]


async def test_coordinator_skips_version_when_unavailable(hass):
    client = AsyncMock()
    client.async_get_status.return_value = RetroArchStatus(available=False, state="unknown")

    coordinator = RetroArchDataUpdateCoordinator(
        hass, client=client, name="RetroArch", scan_interval=5, ram_sensors=[]
    )

    data = await coordinator._async_update_data()

    assert data.available is False
    client.async_get_version.assert_not_called()
    client.async_read_memory.assert_not_called()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_coordinator.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.retroarch.coordinator'`

- [ ] **Step 3: Write `coordinator.py`**

Create `custom_components/retroarch/coordinator.py`:

```python
"""DataUpdateCoordinator for the RetroArch integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import RetroArchClient, RetroArchStatus
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type RetroArchConfigEntry = ConfigEntry["RetroArchDataUpdateCoordinator"]


class RetroArchDataUpdateCoordinator(DataUpdateCoordinator[RetroArchStatus]):
    """Polls one RetroArch instance and shares a RetroArchStatus snapshot."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: RetroArchClient,
        name: str,
        scan_interval: int,
        ram_sensors: list[dict],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {name}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.device_name = name
        self.ram_sensors = ram_sensors
        self._version: str | None = None

    async def _async_update_data(self) -> RetroArchStatus:
        status = await self.client.async_get_status()

        if not status.available:
            return status

        # Version rarely changes; fetch once and cache.
        if self._version is None:
            self._version = await self.client.async_get_version()
        status.version = self._version

        for sensor in self.ram_sensors:
            address = int(str(sensor["address"]), 16)
            size = int(sensor["size"])
            value = await self.client.async_read_memory(address, size)
            if value is not None:
                status.ram[sensor["name"]] = value

        return status
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_coordinator.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/coordinator.py tests/test_coordinator.py
git commit -m "feat: add data update coordinator"
```

---

## Task 6: Manifest, strings, translations

**Files:**
- Create: `custom_components/retroarch/manifest.json`
- Create: `custom_components/retroarch/strings.json`
- Create: `custom_components/retroarch/translations/en.json`
- Create: `custom_components/retroarch/translations/pt-BR.json`

> **CI gotcha (hassfest):** manifest keys must be ordered `domain`, `name` first, then the remaining keys **alphabetically**. Keep this exact order or `hassfest` fails.

- [ ] **Step 1: Write `manifest.json`**

Create `custom_components/retroarch/manifest.json`:

```json
{
  "domain": "retroarch",
  "name": "RetroArch",
  "codeowners": ["@hudsonbrendon"],
  "config_flow": true,
  "documentation": "https://github.com/hudsonbrendon/ha-retroarch",
  "integration_type": "device",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/hudsonbrendon/ha-retroarch/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

- [ ] **Step 2: Write `strings.json`**

Create `custom_components/retroarch/strings.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "RetroArch",
        "menu_options": {
          "discover": "Search the network automatically",
          "manual": "Enter connection details manually"
        }
      },
      "discover": {
        "title": "Discovered RetroArch instances",
        "description": "Pick a RetroArch instance found on your network.",
        "data": {
          "host": "Host",
          "port": "Port",
          "name": "Name"
        }
      },
      "manual": {
        "title": "Connect to RetroArch",
        "description": "Enable the Network Control Interface in retroarch.cfg (network_cmd_enable = true).",
        "data": {
          "host": "Host",
          "port": "Port",
          "name": "Name"
        }
      }
    },
    "error": {
      "cannot_connect": "Could not reach RetroArch. Check the host, port, and that network commands are enabled."
    },
    "abort": {
      "already_configured": "This RetroArch instance is already configured."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "RetroArch options",
        "menu_options": {
          "settings": "Polling settings",
          "add_ram_sensor": "Add a RAM sensor",
          "remove_ram_sensor": "Remove a RAM sensor"
        }
      },
      "settings": {
        "data": {
          "scan_interval": "Polling interval (seconds)"
        }
      },
      "add_ram_sensor": {
        "title": "Add RAM sensor",
        "data": {
          "name": "Sensor name",
          "address": "Memory address (hex, e.g. 7e0019)",
          "size": "Number of bytes",
          "signed": "Signed value",
          "big_endian": "Big-endian byte order",
          "scale": "Scale factor",
          "unit": "Unit of measurement"
        }
      },
      "remove_ram_sensor": {
        "title": "Remove RAM sensor",
        "data": {
          "name": "Sensor to remove"
        }
      }
    }
  }
}
```

- [ ] **Step 3: Write `translations/en.json`**

Create `custom_components/retroarch/translations/en.json` with the same content as `strings.json` (copy it verbatim).

- [ ] **Step 4: Write `translations/pt-BR.json`**

Create `custom_components/retroarch/translations/pt-BR.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "RetroArch",
        "menu_options": {
          "discover": "Procurar na rede automaticamente",
          "manual": "Inserir os dados de conexão manualmente"
        }
      },
      "discover": {
        "title": "Instâncias do RetroArch encontradas",
        "description": "Escolha uma instância do RetroArch encontrada na sua rede.",
        "data": {
          "host": "Host",
          "port": "Porta",
          "name": "Nome"
        }
      },
      "manual": {
        "title": "Conectar ao RetroArch",
        "description": "Ative a interface de comandos de rede no retroarch.cfg (network_cmd_enable = true).",
        "data": {
          "host": "Host",
          "port": "Porta",
          "name": "Nome"
        }
      }
    },
    "error": {
      "cannot_connect": "Não foi possível alcançar o RetroArch. Verifique host, porta e se os comandos de rede estão ativados."
    },
    "abort": {
      "already_configured": "Esta instância do RetroArch já está configurada."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Opções do RetroArch",
        "menu_options": {
          "settings": "Configurações de polling",
          "add_ram_sensor": "Adicionar sensor de RAM",
          "remove_ram_sensor": "Remover sensor de RAM"
        }
      },
      "settings": {
        "data": {
          "scan_interval": "Intervalo de polling (segundos)"
        }
      },
      "add_ram_sensor": {
        "title": "Adicionar sensor de RAM",
        "data": {
          "name": "Nome do sensor",
          "address": "Endereço de memória (hex, ex.: 7e0019)",
          "size": "Número de bytes",
          "signed": "Valor com sinal",
          "big_endian": "Ordem big-endian",
          "scale": "Fator de escala",
          "unit": "Unidade de medida"
        }
      },
      "remove_ram_sensor": {
        "title": "Remover sensor de RAM",
        "data": {
          "name": "Sensor a remover"
        }
      }
    }
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/manifest.json custom_components/retroarch/strings.json custom_components/retroarch/translations
git commit -m "feat: add manifest, strings, and translations"
```

---

## Task 7: Config flow + Options flow + entry setup/unload

**Files:**
- Create: `custom_components/retroarch/config_flow.py`
- Replace: `custom_components/retroarch/__init__.py`
- Test: `tests/test_config_flow.py`, `tests/test_init.py`, `tests/const.py`

- [ ] **Step 1: Write a shared test constants file**

Create `tests/const.py`:

```python
"""Shared test constants."""
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

MOCK_CONFIG = {
    CONF_HOST: "192.168.1.50",
    CONF_PORT: 55355,
    CONF_NAME: "RetroArch",
}
```

- [ ] **Step 2: Write the failing config flow test**

Create `tests/test_config_flow.py`:

```python
"""Tests for the RetroArch config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def test_menu_then_manual_success(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.MENU

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "manual"

    with patch(
        "custom_components.retroarch.config_flow.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "RetroArch"
    assert result["data"] == MOCK_CONFIG


async def test_manual_cannot_connect(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    with patch(
        "custom_components.retroarch.config_flow.RetroArchClient.async_get_version",
        new=AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_discovery_flow_success(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.retroarch.config_flow.async_discover",
        new=AsyncMock(return_value={"192.168.1.50": "1.19.1"}),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "discover"}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "discover"

    with patch(
        "custom_components.retroarch.config_flow.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "192.168.1.50", "port": 55355, "name": "RetroArch"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "192.168.1.50"


async def test_discovery_empty_falls_back_to_manual(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.retroarch.config_flow.async_discover",
        new=AsyncMock(return_value={}),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "discover"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "manual"
```

- [ ] **Step 3: Run to verify it fails**

Run: `python -m pytest tests/test_config_flow.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.retroarch.config_flow'`

- [ ] **Step 4: Write `config_flow.py`**

Create `custom_components/retroarch/config_flow.py`:

```python
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
            menu_options=["settings", "add_ram_sensor", "remove_ram_sensor"],
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
```

- [ ] **Step 5: Write the failing init test**

Create `tests/test_init.py`:

```python
"""Tests for setup and unload of the RetroArch integration."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def test_setup_and_unload(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
```

- [ ] **Step 6: Replace `__init__.py` with real setup/unload**

Replace `custom_components/retroarch/__init__.py`:

```python
"""The RetroArch integration."""
from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant

from .api import RetroArchClient
from .const import (
    CONF_RAM_SENSORS,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: RetroArchConfigEntry) -> bool:
    """Set up RetroArch from a config entry."""
    client = RetroArchClient(entry.data[CONF_HOST], entry.data[CONF_PORT])

    coordinator = RetroArchDataUpdateCoordinator(
        hass,
        client=client,
        name=entry.data.get(CONF_NAME, DEFAULT_NAME),
        scan_interval=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ram_sensors=entry.options.get(CONF_RAM_SENSORS, []),
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Imported here (not at module top) so the package stays importable during
    # incremental development before services.py exists; it always ships in releases.
    from .services import async_setup_services

    async_setup_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RetroArchConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.client.close()
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: RetroArchConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
```

> **Execution note (subagent-driven build order):** Because `async_setup_entry` forwards to every platform in `PLATFORMS` and lazily imports `services`, a full setup needs those modules to exist. Build in this order: Task 7 → Task 8 (entity) → Task 14 (services) → Tasks 9–13 (platforms) → Task 15. Each platform test wraps its setup in `patch("custom_components.retroarch.PLATFORMS", [Platform.<X>])` so it forwards only its own platform; the services test patches `PLATFORMS` to `[]`. `test_init.py` (full `PLATFORMS`) runs only in Task 15, once every platform module exists.

> Note: We intentionally do NOT raise `ConfigEntryNotReady` when RetroArch is unreachable at the first refresh. RetroArch is a desktop app that is frequently closed; the integration should still load with its entities showing `unavailable` (the base entity's `available` property gates on `coordinator.data.available`, added in Task 8). Connectivity was already validated during the config flow, and the coordinator from Task 5 returns an unavailable `RetroArchStatus` (it does not raise) — so `async_config_entry_first_refresh()` completes normally and the entry loads. **No change to `coordinator.py` is needed here** (do not add `UpdateFailed`); this preserves the Task 5 unit test `test_coordinator_skips_version_when_unavailable`, which calls `_async_update_data` directly on a coordinator whose `data` is still `None`.

- [ ] **Step 7: Run the flow + init tests (services.py not written yet — expect ImportError)**

Run: `python -m pytest tests/test_config_flow.py -q`
Expected: 4 passed (config_flow has no dependency on services). These cover menu → manual success, manual cannot-connect, discovery success, and discovery → manual fallback.

`tests/test_init.py` will fail until `services.py` (Task 14) and all platform modules (Tasks 8–13) exist, because `async_setup_entry` forwards to every platform and registers services. That is expected; `test_init.py` is created now but only RUN in Task 15's full-suite step.

- [ ] **Step 8: Commit**

```bash
git add custom_components/retroarch/config_flow.py custom_components/retroarch/__init__.py tests/test_config_flow.py tests/test_init.py tests/const.py
git commit -m "feat: add config/options flow and entry setup"
```

---

## Task 8: Base entity

**Files:**
- Create: `custom_components/retroarch/entity.py`

- [ ] **Step 1: Write `entity.py`**

Create `custom_components/retroarch/entity.py`:

```python
"""Base entity for the RetroArch integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import RetroArchDataUpdateCoordinator


class RetroArchEntity(CoordinatorEntity[RetroArchDataUpdateCoordinator]):
    """Common device info + availability for RetroArch entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RetroArchDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model="RetroArch",
            sw_version=coordinator.data.version if coordinator.data else None,
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.available
```

> `coordinator.config_entry` is automatically set by `DataUpdateCoordinator` when created inside `async_setup_entry` (HA wires it from the running task). It is available because the coordinator is constructed within the config entry setup context.

- [ ] **Step 2: Commit**

```bash
git add custom_components/retroarch/entity.py
git commit -m "feat: add base entity with device info"
```

---

## Task 9: Status sensors + RAM sensors

**Files:**
- Create: `custom_components/retroarch/sensor.py`
- Test: `tests/test_sensor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sensor.py`:

```python
"""Tests for RetroArch sensors."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import CONF_RAM_SENSORS, DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass, status, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, options=options or {}, unique_id="192.168.1.50:55355"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_read_memory",
        new=AsyncMock(return_value=[0x05]),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_game_sensor_reports_title(hass):
    status = RetroArchStatus(
        available=True, state="playing", system="nes", game="Metroid", crc32="DEADBEEF"
    )
    await _setup(hass, status)
    state = hass.states.get("sensor.retroarch_game")
    assert state.state == "Metroid"


async def test_system_sensor_reports_core(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    await _setup(hass, status)
    assert hass.states.get("sensor.retroarch_system").state == "nes"


async def test_ram_sensor_reports_value(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    options = {CONF_RAM_SENSORS: [{"name": "Lives", "address": "7e0019", "size": 1, "scale": 1.0, "unit": "lives", "signed": False, "big_endian": False}]}
    await _setup(hass, status, options)
    state = hass.states.get("sensor.retroarch_lives")
    assert state.state == "5"
    assert state.attributes["unit_of_measurement"] == "lives"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_sensor.py -q`
Expected: FAIL — sensor platform missing; entities not created.

- [ ] **Step 3: Write `sensor.py`**

Create `custom_components/retroarch/sensor.py`:

```python
"""Sensor platform for RetroArch."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import RetroArchStatus
from .const import (
    CONF_RAM_ADDRESS,
    CONF_RAM_BIG_ENDIAN,
    CONF_RAM_NAME,
    CONF_RAM_SCALE,
    CONF_RAM_SENSORS,
    CONF_RAM_SIGNED,
    CONF_RAM_UNIT,
)
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchSensorDescription(SensorEntityDescription):
    """Describes a status sensor."""

    value_fn: Callable[[RetroArchStatus], StateType]


STATUS_SENSORS: tuple[RetroArchSensorDescription, ...] = (
    RetroArchSensorDescription(
        key="status",
        translation_key="status",
        name="Status",
        value_fn=lambda data: data.state,
    ),
    RetroArchSensorDescription(
        key="game",
        name="Game",
        value_fn=lambda data: data.game,
    ),
    RetroArchSensorDescription(
        key="system",
        name="System",
        value_fn=lambda data: data.system,
    ),
    RetroArchSensorDescription(
        key="crc32",
        name="Content CRC32",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.crc32,
    ),
    RetroArchSensorDescription(
        key="version",
        name="Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.version,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RetroArch sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        RetroArchSensor(coordinator, description) for description in STATUS_SENSORS
    ]
    for ram in entry.options.get(CONF_RAM_SENSORS, []):
        entities.append(RetroArchRamSensor(coordinator, ram))
    async_add_entities(entities)


def _decode(values: list[int], *, signed: bool, big_endian: bool, scale: float) -> float | int:
    raw = int.from_bytes(
        bytes(b & 0xFF for b in values),
        byteorder="big" if big_endian else "little",
        signed=signed,
    )
    result = raw * scale
    return int(result) if scale == 1.0 else result


class RetroArchSensor(RetroArchEntity, SensorEntity):
    """A status sensor backed by the coordinator snapshot."""

    entity_description: RetroArchSensorDescription

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)


class RetroArchRamSensor(RetroArchEntity, SensorEntity):
    """A user-configured sensor reading a value from core RAM."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: RetroArchDataUpdateCoordinator, config: dict
    ) -> None:
        super().__init__(coordinator)
        self._config = config
        name = config[CONF_RAM_NAME]
        self._attr_name = name
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_ram_{config[CONF_RAM_ADDRESS]}_{name}"
        )
        unit = config.get(CONF_RAM_UNIT) or None
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> StateType:
        values = self.coordinator.data.ram.get(self._config[CONF_RAM_NAME])
        if not values:
            return None
        return _decode(
            values,
            signed=self._config.get(CONF_RAM_SIGNED, False),
            big_endian=self._config.get(CONF_RAM_BIG_ENDIAN, False),
            scale=float(self._config.get(CONF_RAM_SCALE, 1.0)),
        )
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_sensor.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/sensor.py tests/test_sensor.py
git commit -m "feat: add status sensors and configurable RAM sensors"
```

---

## Task 10: Binary sensors

**Files:**
- Create: `custom_components/retroarch/binary_sensor.py`
- Test: `tests/test_binary_sensor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_binary_sensor.py`:

```python
"""Tests for RetroArch binary sensors."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass, status):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_playing_binary_sensor_on(hass):
    await _setup(hass, RetroArchStatus(available=True, state="playing", game="Metroid"))
    assert hass.states.get("binary_sensor.retroarch_playing").state == "on"
    assert hass.states.get("binary_sensor.retroarch_paused").state == "off"


async def test_paused_binary_sensor_on(hass):
    await _setup(hass, RetroArchStatus(available=True, state="paused", game="Metroid"))
    assert hass.states.get("binary_sensor.retroarch_playing").state == "off"
    assert hass.states.get("binary_sensor.retroarch_paused").state == "on"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_binary_sensor.py -q`
Expected: FAIL — binary_sensor platform missing.

- [ ] **Step 3: Write `binary_sensor.py`**

Create `custom_components/retroarch/binary_sensor.py`:

```python
"""Binary sensor platform for RetroArch."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RetroArchStatus
from .const import STATE_PAUSED, STATE_PLAYING
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchBinaryDescription(BinarySensorEntityDescription):
    """Describes a binary sensor."""

    value_fn: Callable[[RetroArchStatus], bool]


BINARY_SENSORS: tuple[RetroArchBinaryDescription, ...] = (
    RetroArchBinaryDescription(
        key="playing",
        name="Playing",
        value_fn=lambda data: data.state == STATE_PLAYING,
    ),
    RetroArchBinaryDescription(
        key="paused",
        name="Paused",
        value_fn=lambda data: data.state == STATE_PAUSED,
    ),
    RetroArchBinaryDescription(
        key="content_loaded",
        name="Content loaded",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.state in (STATE_PLAYING, STATE_PAUSED),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        RetroArchBinarySensor(coordinator, description) for description in BINARY_SENSORS
    )


class RetroArchBinarySensor(RetroArchEntity, BinarySensorEntity):
    """Binary sensor backed by the coordinator snapshot."""

    entity_description: RetroArchBinaryDescription

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchBinaryDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_binary_sensor.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/binary_sensor.py tests/test_binary_sensor.py
git commit -m "feat: add playing/paused/content-loaded binary sensors"
```

---

## Task 11: Buttons (all fire-and-forget commands)

**Files:**
- Create: `custom_components/retroarch/button.py`
- Test: `tests/test_button.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_button.py`:

```python
"""Tests for RetroArch buttons."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="playing", game="X")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_reset_button_sends_reset(hass):
    await _setup(hass)
    with patch(
        "custom_components.retroarch.button.RetroArchDataUpdateCoordinator.client",
        create=True,
    ):
        pass  # placeholder removed below

    with patch.object(
        hass.data.setdefault("_unused", object()), "__class__", object
    ):
        pass


async def test_reset_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.retroarch_reset"},
            blocking=True,
        )
    mock_send.assert_awaited_once_with("RESET")


async def test_screenshot_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.retroarch_screenshot"},
            blocking=True,
        )
    mock_send.assert_awaited_once_with("SCREENSHOT")
```

> Delete the two placeholder test bodies (`test_reset_button_sends_reset` and the inner `with patch.object(... "_unused" ...)`) — they were scaffolding. Keep only `test_reset_button_press` and `test_screenshot_button_press`. (Listed here to make the final file unambiguous: the file should contain exactly the imports, `_setup`, `test_reset_button_press`, and `test_screenshot_button_press`.)

Final `tests/test_button.py` content:

```python
"""Tests for RetroArch buttons."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="playing", game="X")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_reset_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.retroarch_reset"}, blocking=True
        )
    mock_send.assert_awaited_once_with("RESET")


async def test_screenshot_button_press(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.retroarch_screenshot"}, blocking=True
        )
    mock_send.assert_awaited_once_with("SCREENSHOT")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_button.py -q`
Expected: FAIL — button platform missing.

- [ ] **Step 3: Write `button.py`**

Create `custom_components/retroarch/button.py`:

```python
"""Button platform for RetroArch (fire-and-forget commands)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchButtonDescription(ButtonEntityDescription):
    """A button that sends one network command."""

    command: str


BUTTONS: tuple[RetroArchButtonDescription, ...] = (
    RetroArchButtonDescription(key="pause_toggle", name="Pause/Resume", command="PAUSE_TOGGLE"),
    RetroArchButtonDescription(key="reset", name="Reset", command="RESET"),
    RetroArchButtonDescription(key="frame_advance", name="Frame advance", command="FRAMEADVANCE"),
    RetroArchButtonDescription(key="save_state", name="Save state", command="SAVE_STATE"),
    RetroArchButtonDescription(key="load_state", name="Load state", command="LOAD_STATE"),
    RetroArchButtonDescription(key="state_slot_plus", name="State slot +", command="STATE_SLOT_PLUS"),
    RetroArchButtonDescription(key="state_slot_minus", name="State slot -", command="STATE_SLOT_MINUS"),
    RetroArchButtonDescription(key="screenshot", name="Screenshot", command="SCREENSHOT"),
    RetroArchButtonDescription(key="fast_forward", name="Fast forward toggle", command="FAST_FORWARD"),
    RetroArchButtonDescription(key="rewind", name="Rewind", command="REWIND"),
    RetroArchButtonDescription(key="slow_motion", name="Slow motion", command="SLOWMOTION"),
    RetroArchButtonDescription(key="ai_service", name="AI service", command="AI_SERVICE"),
    RetroArchButtonDescription(key="menu_toggle", name="Menu toggle", command="MENU_TOGGLE"),
    RetroArchButtonDescription(key="close_content", name="Close content", command="CLOSE_CONTENT"),
    RetroArchButtonDescription(key="quit", name="Quit RetroArch", command="QUIT", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="disk_eject_toggle", name="Disk eject toggle", command="DISK_EJECT_TOGGLE"),
    RetroArchButtonDescription(key="disk_next", name="Disk next", command="DISK_NEXT"),
    RetroArchButtonDescription(key="disk_prev", name="Disk previous", command="DISK_PREV"),
    RetroArchButtonDescription(key="shader_next", name="Shader next", command="SHADER_NEXT"),
    RetroArchButtonDescription(key="shader_prev", name="Shader previous", command="SHADER_PREV"),
    RetroArchButtonDescription(key="shader_toggle", name="Shader toggle", command="SHADER_TOGGLE"),
    RetroArchButtonDescription(key="cheat_toggle", name="Cheat toggle", command="CHEAT_TOGGLE"),
    RetroArchButtonDescription(key="cheat_index_plus", name="Cheat index +", command="CHEAT_INDEX_PLUS"),
    RetroArchButtonDescription(key="cheat_index_minus", name="Cheat index -", command="CHEAT_INDEX_MINUS"),
    RetroArchButtonDescription(key="volume_up", name="Volume up", command="VOLUME_UP"),
    RetroArchButtonDescription(key="volume_down", name="Volume down", command="VOLUME_DOWN"),
    RetroArchButtonDescription(key="recording_toggle", name="Recording toggle", command="RECORDING_TOGGLE"),
    RetroArchButtonDescription(key="streaming_toggle", name="Streaming toggle", command="STREAMING_TOGGLE"),
    RetroArchButtonDescription(key="fps_toggle", name="FPS display toggle", command="FPS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="statistics_toggle", name="Statistics toggle", command="STATISTICS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="game_focus_toggle", name="Game focus toggle", command="GAME_FOCUS_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="grab_mouse_toggle", name="Grab mouse toggle", command="GRAB_MOUSE_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="runahead_toggle", name="Run-ahead toggle", command="RUNAHEAD_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchButtonDescription(key="vrr_runloop_toggle", name="VRR runloop toggle", command="VRR_RUNLOOP_TOGGLE", entity_category=EntityCategory.CONFIG),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RetroArchButton(coordinator, description) for description in BUTTONS)


class RetroArchButton(RetroArchEntity, ButtonEntity):
    """A button that sends a single UDP command on press."""

    entity_description: RetroArchButtonDescription

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    async def async_press(self) -> None:
        await self.coordinator.client.send_command(self.entity_description.command)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_button.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/button.py tests/test_button.py
git commit -m "feat: add control buttons for all network commands"
```

---

## Task 12: Optimistic toggle switches

**Files:**
- Create: `custom_components/retroarch/switch.py`
- Test: `tests/test_switch.py`

> RetroArch only exposes `*_TOGGLE` commands (no way to read fast-forward/mute/fullscreen state over UDP). These switches are therefore **optimistic** (`assumed_state = True`): they track an internal boolean and send the toggle command only when the requested state differs from the assumed state.

- [ ] **Step 1: Write the failing test**

Create `tests/test_switch.py`:

```python
"""Tests for RetroArch optimistic switches."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="playing", game="X")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_fast_forward_turn_on_sends_toggle(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.retroarch_fast_forward"}, blocking=True
        )
    mock_send.assert_awaited_once_with("FAST_FORWARD")
    assert hass.states.get("switch.retroarch_fast_forward").state == "on"


async def test_fast_forward_turn_on_twice_only_toggles_once(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.retroarch_fast_forward"}, blocking=True
        )
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.retroarch_fast_forward"}, blocking=True
        )
    assert mock_send.await_count == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_switch.py -q`
Expected: FAIL — switch platform missing.

- [ ] **Step 3: Write `switch.py`**

Create `custom_components/retroarch/switch.py`:

```python
"""Switch platform for RetroArch (optimistic toggles)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


@dataclass(frozen=True, kw_only=True)
class RetroArchSwitchDescription(SwitchEntityDescription):
    """An optimistic switch backed by a single TOGGLE command."""

    command: str


SWITCHES: tuple[RetroArchSwitchDescription, ...] = (
    RetroArchSwitchDescription(key="fast_forward", name="Fast forward", command="FAST_FORWARD"),
    RetroArchSwitchDescription(key="slow_motion", name="Slow motion", command="SLOWMOTION"),
    RetroArchSwitchDescription(key="mute", name="Mute", command="MUTE"),
    RetroArchSwitchDescription(key="fullscreen", name="Fullscreen", command="FULLSCREEN_TOGGLE", entity_category=EntityCategory.CONFIG),
    RetroArchSwitchDescription(key="pause", name="Pause", command="PAUSE_TOGGLE"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RetroArchSwitch(coordinator, description) for description in SWITCHES)


class RetroArchSwitch(RetroArchEntity, SwitchEntity):
    """Optimistic switch: tracks an internal bool, toggles only on change."""

    entity_description: RetroArchSwitchDescription
    _attr_assumed_state = True

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: RetroArchSwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self._attr_is_on:
            await self.coordinator.client.send_command(self.entity_description.command)
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._attr_is_on:
            await self.coordinator.client.send_command(self.entity_description.command)
            self._attr_is_on = False
            self.async_write_ha_state()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_switch.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/switch.py tests/test_switch.py
git commit -m "feat: add optimistic toggle switches"
```

---

## Task 13: Media player

**Files:**
- Create: `custom_components/retroarch/media_player.py`
- Test: `tests/test_media_player.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_media_player.py`:

```python
"""Tests for the RetroArch media player."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass, status):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_media_player_playing_state_and_title(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    await _setup(hass, status)
    state = hass.states.get("media_player.retroarch")
    assert state.state == "playing"
    assert state.attributes["media_title"] == "Metroid"
    assert state.attributes["app_name"] == "nes"


async def test_media_player_paused_state(hass):
    status = RetroArchStatus(available=True, state="paused", system="nes", game="Metroid")
    await _setup(hass, status)
    assert hass.states.get("media_player.retroarch").state == "paused"


async def test_media_player_contentless_is_idle(hass):
    status = RetroArchStatus(available=True, state="contentless")
    await _setup(hass, status)
    assert hass.states.get("media_player.retroarch").state == "idle"


async def test_media_player_pause_sends_toggle(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    entry = await _setup(hass, status)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "media_player", "media_pause", {"entity_id": "media_player.retroarch"}, blocking=True
        )
    mock_send.assert_awaited_once_with("PAUSE_TOGGLE")


async def test_media_player_stop_closes_content(hass):
    status = RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")
    entry = await _setup(hass, status)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            "media_player", "media_stop", {"entity_id": "media_player.retroarch"}, blocking=True
        )
    mock_send.assert_awaited_once_with("CLOSE_CONTENT")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_media_player.py -q`
Expected: FAIL — media_player platform missing.

- [ ] **Step 3: Write `media_player.py`**

Create `custom_components/retroarch/media_player.py`:

```python
"""Media player platform for RetroArch."""
from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import STATE_PAUSED, STATE_PLAYING
from .coordinator import RetroArchConfigEntry, RetroArchDataUpdateCoordinator
from .entity import RetroArchEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RetroArchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RetroArchMediaPlayer(entry.runtime_data)])


class RetroArchMediaPlayer(RetroArchEntity, MediaPlayerEntity):
    """Represents the running game as a media player."""

    _attr_name = None  # use the device name
    _attr_media_content_type = MediaType.GAME
    _attr_supported_features = (
        MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_STEP
    )

    def __init__(self, coordinator: RetroArchDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_media_player"

    @property
    def state(self) -> MediaPlayerState:
        data = self.coordinator.data
        if data.state == STATE_PLAYING:
            return MediaPlayerState.PLAYING
        if data.state == STATE_PAUSED:
            return MediaPlayerState.PAUSED
        return MediaPlayerState.IDLE

    @property
    def media_title(self) -> str | None:
        return self.coordinator.data.game

    @property
    def app_name(self) -> str | None:
        return self.coordinator.data.system

    async def async_media_play(self) -> None:
        if self.coordinator.data.state == STATE_PAUSED:
            await self.coordinator.client.send_command("PAUSE_TOGGLE")

    async def async_media_pause(self) -> None:
        if self.coordinator.data.state == STATE_PLAYING:
            await self.coordinator.client.send_command("PAUSE_TOGGLE")

    async def async_media_stop(self) -> None:
        await self.coordinator.client.send_command("CLOSE_CONTENT")

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.client.send_command("MUTE")

    async def async_volume_up(self) -> None:
        await self.coordinator.client.send_command("VOLUME_UP")

    async def async_volume_down(self) -> None:
        await self.coordinator.client.send_command("VOLUME_DOWN")
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_media_player.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/media_player.py tests/test_media_player.py
git commit -m "feat: add media_player entity"
```

---

## Task 14: Services (raw command, memory, messages, slots, shader, core)

**Files:**
- Create: `custom_components/retroarch/services.py`
- Create: `custom_components/retroarch/services.yaml`
- Test: `tests/test_services.py`
- Modify: `strings.json` / `translations/en.json` (add `services` block — optional but recommended)

- [ ] **Step 1: Write the failing test**

Create `tests/test_services.py`:

```python
"""Tests for RetroArch services."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN

from .const import MOCK_CONFIG


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="playing", game="X")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_send_command_service(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    device_id = next(iter(coordinator.config_entry.runtime_data.config_entry.data and [None]))  # noqa
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            DOMAIN,
            "send_command",
            {"config_entry_id": entry.entry_id, "command": "RESET"},
            blocking=True,
        )
    mock_send.assert_awaited_once_with("RESET")


async def test_read_memory_service_returns_data(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(
        coordinator.client, "async_read_memory", new=AsyncMock(return_value=[10, 20])
    ):
        result = await hass.services.async_call(
            DOMAIN,
            "read_memory",
            {"config_entry_id": entry.entry_id, "address": "7e0019", "size": 2},
            blocking=True,
            return_response=True,
        )
    assert result["data"] == [10, 20]
    assert result["hex"] == "0a 14"


async def test_write_memory_service(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "async_write_memory", new=AsyncMock()) as mock_write:
        await hass.services.async_call(
            DOMAIN,
            "write_memory",
            {"config_entry_id": entry.entry_id, "address": "7e0019", "data": [10, 255]},
            blocking=True,
        )
    mock_write.assert_awaited_once_with(0x7E0019, [10, 255])


async def test_show_message_service(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            DOMAIN,
            "show_message",
            {"config_entry_id": entry.entry_id, "message": "Hello"},
            blocking=True,
        )
    mock_send.assert_awaited_once_with("SHOW_MSG Hello")
```

> Remove the bogus `device_id = ...` line from `test_send_command_service` — it was an editing artifact. The final `test_send_command_service` body is just the `with patch.object(...)` block and the assertion.

Final `test_send_command_service`:

```python
async def test_send_command_service(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    with patch.object(coordinator.client, "send_command", new=AsyncMock()) as mock_send:
        await hass.services.async_call(
            DOMAIN,
            "send_command",
            {"config_entry_id": entry.entry_id, "command": "RESET"},
            blocking=True,
        )
    mock_send.assert_awaited_once_with("RESET")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_services.py tests/test_init.py -q`
Expected: FAIL — `services.py` missing (and `test_init.py` now imports it via `__init__.py`).

- [ ] **Step 3: Write `services.py`**

Create `custom_components/retroarch/services.py`:

```python
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

from .const import DOMAIN

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
SERVICE_SHOW_MESSAGE = "show_message"
SERVICE_LOAD_STATE_SLOT = "load_state_slot"
SERVICE_SET_SHADER = "set_shader"
SERVICE_LOAD_CORE = "load_core"

_ENTRY = {vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string}

SEND_COMMAND_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_COMMAND): cv.string})
READ_MEMORY_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Required(ATTR_ADDRESS): cv.string, vol.Required(ATTR_SIZE): vol.All(int, vol.Range(min=1, max=256))}
)
WRITE_MEMORY_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Required(ATTR_ADDRESS): cv.string, vol.Required(ATTR_DATA): [vol.All(int, vol.Range(min=0, max=255))]}
)
SHOW_MESSAGE_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_MESSAGE): cv.string})
LOAD_STATE_SLOT_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_SLOT): vol.All(int, vol.Range(min=0))})
SET_SHADER_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_PATH): cv.string})
LOAD_CORE_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_PATH): cv.string})


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

    async def handle_show_message(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"SHOW_MSG {call.data[ATTR_MESSAGE]}")

    async def handle_load_state_slot(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"LOAD_STATE_SLOT {call.data[ATTR_SLOT]}")

    async def handle_set_shader(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"SET_SHADER {call.data[ATTR_PATH]}")

    async def handle_load_core(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.send_command(f"LOAD_CORE {call.data[ATTR_PATH]}")

    hass.services.async_register(DOMAIN, SERVICE_SEND_COMMAND, handle_send_command, schema=SEND_COMMAND_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_READ_MEMORY, handle_read_memory, schema=READ_MEMORY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, SERVICE_WRITE_MEMORY, handle_write_memory, schema=WRITE_MEMORY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SHOW_MESSAGE, handle_show_message, schema=SHOW_MESSAGE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_LOAD_STATE_SLOT, handle_load_state_slot, schema=LOAD_STATE_SLOT_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_SHADER, handle_set_shader, schema=SET_SHADER_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_LOAD_CORE, handle_load_core, schema=LOAD_CORE_SCHEMA)
```

- [ ] **Step 4: Write `services.yaml`**

Create `custom_components/retroarch/services.yaml`:

```yaml
send_command:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: retroarch
    command:
      required: true
      example: "RESET"
      selector:
        text:

read_memory:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: retroarch
    address:
      required: true
      example: "7e0019"
      selector:
        text:
    size:
      required: true
      default: 1
      selector:
        number:
          min: 1
          max: 256
          mode: box

write_memory:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: retroarch
    address:
      required: true
      example: "7e0019"
      selector:
        text:
    data:
      required: true
      example: "[10, 255]"
      selector:
        object:

show_message:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: retroarch
    message:
      required: true
      selector:
        text:

load_state_slot:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: retroarch
    slot:
      required: true
      selector:
        number:
          min: 0
          max: 999
          mode: box

set_shader:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: retroarch
    path:
      required: true
      selector:
        text:

load_core:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: retroarch
    path:
      required: true
      selector:
        text:
```

- [ ] **Step 5: Run the service + init tests**

Run: `python -m pytest tests/test_services.py tests/test_init.py -q`
Expected: all pass (5 service tests + 1 init test).

- [ ] **Step 6: Commit**

```bash
git add custom_components/retroarch/services.py custom_components/retroarch/services.yaml tests/test_services.py
git commit -m "feat: add raw command, memory, and helper services"
```

---

## Task 15: Options flow test + full reload coverage

**Files:**
- Modify: `tests/test_config_flow.py` (append options-flow tests)

- [ ] **Step 1: Append the failing options-flow tests**

Append to `tests/test_config_flow.py`:

```python
from unittest.mock import AsyncMock as _AsyncMock  # alias to avoid shadowing above

from homeassistant.const import CONF_SCAN_INTERVAL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import CONF_RAM_SENSORS


async def _load_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_options_add_ram_sensor(hass):
    entry = await _load_entry(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_read_memory",
        new=_AsyncMock(return_value=[1]),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_ram_sensor"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Lives",
                "address": "7e0019",
                "size": 1,
                "signed": False,
                "big_endian": False,
                "scale": 1.0,
                "unit": "lives",
            },
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_RAM_SENSORS][0]["name"] == "Lives"


async def test_options_settings_changes_interval(hass):
    entry = await _load_entry(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "settings"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 10}
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_SCAN_INTERVAL] == 10
```

- [ ] **Step 2: Run to verify**

Run: `python -m pytest tests/test_config_flow.py -q`
Expected: 4 passed (2 from Task 7 + 2 new). If the reload after options change errors, confirm `_async_reload_entry` is registered in `__init__.py` (Task 7, Step 6).

- [ ] **Step 3: Run the full suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_config_flow.py
git commit -m "test: cover options flow (RAM sensors + interval)"
```

---

## Task 16: HACS metadata, README, CI

**Files:**
- Create: `hacs.json`
- Create: `README.md`
- Create: `LICENSE`
- Create: `.github/workflows/validate.yaml`
- Create: `.github/workflows/tests.yaml`

> **CI gotcha (HACS):** the GitHub repo must have **topics** set (e.g. `home-assistant`, `hacs`, `retroarch`, `integration`) or HACS validation fails. Set them with `gh repo edit --add-topic` after the repo exists on GitHub (Step 6).

- [ ] **Step 1: Write `hacs.json`**

Create `hacs.json`:

```json
{
  "name": "RetroArch",
  "render_readme": true,
  "homeassistant": "2024.12.0"
}
```

- [ ] **Step 2: Write `validate.yaml`**

Create `.github/workflows/validate.yaml`:

```yaml
name: Validate

on:
  push:
  pull_request:
  schedule:
    - cron: "0 0 * * *"

jobs:
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration
```

- [ ] **Step 3: Write `tests.yaml`**

Create `.github/workflows/tests.yaml`:

```yaml
name: Tests

on:
  push:
  pull_request:

jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements_test.txt
      - run: python -m pytest -q
```

- [ ] **Step 4: Write `README.md`**

Create `README.md`:

````markdown
# RetroArch — Home Assistant Integration

Control and monitor a [RetroArch](https://www.retroarch.com/) instance from Home Assistant over its UDP Network Control Interface.

## Features

- **media_player** — current game as title, system/core as app name, play/pause/stop, volume up/down/mute.
- **Sensors** — status, current game, system/core, content CRC32, RetroArch version.
- **Binary sensors** — playing, paused, content loaded.
- **Buttons** — reset, pause/resume, save/load state, state slot ±, screenshot, fast forward, rewind, slow motion, AI service, menu, close content, quit, disk eject/next/prev, shader next/prev/toggle, cheat toggle/index ±, volume ±, recording/streaming toggle, FPS/statistics/game-focus/grab-mouse/run-ahead/VRR toggles.
- **Switches** (optimistic) — fast forward, slow motion, mute, fullscreen, pause.
- **Auto-discovery** — finds RetroArch instances on your LAN via a UDP `VERSION` broadcast probe; manual host/port entry as fallback.
- **Configurable RAM sensors** — read live game values (lives, score, HP…) by memory address via the Options flow.
- **Services** — `retroarch.send_command`, `retroarch.read_memory` (returns data), `retroarch.write_memory`, `retroarch.show_message`, `retroarch.load_state_slot`, `retroarch.set_shader`, `retroarch.load_core`.

## RetroArch setup

In `retroarch.cfg` (or Settings → Network in the UI):

```
network_cmd_enable = "true"
network_cmd_port = "55355"
```

Restart RetroArch. Make sure the host/port is reachable from your Home Assistant machine.

## Installation (HACS)

1. HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/hudsonbrendon/ha-retroarch` as an **Integration**.
3. Install **RetroArch**, restart Home Assistant.
4. Settings → Devices & Services → Add Integration → **RetroArch**. Choose **Search the network automatically** to pick a discovered instance, or **Enter connection details manually** to type the host and port.

## RAM sensors

Settings → Devices & Services → RetroArch → Configure → **Add a RAM sensor**. Provide a name, hex address (e.g. `7e0019`), byte count, and optional signed/big-endian/scale/unit. Addresses are core-specific — consult RetroAchievements memory maps or cheat files for your game.

## Notes

- Switches are optimistic: RetroArch's UDP interface only exposes toggle commands, so HA cannot read fast-forward/mute/fullscreen state.
- `read_memory`/`write_memory` use `READ_CORE_RAM`/`WRITE_CORE_RAM`; support depends on the loaded core.
````

- [ ] **Step 5: Write `LICENSE`**

Create `LICENSE` (MIT):

```text
MIT License

Copyright (c) 2026 Hudson Brendon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 6: Create the GitHub repo and set topics**

```bash
cd ~/Github/ha-retroarch
git add -A
git commit -m "chore: add HACS metadata, README, license, and CI workflows"
gh repo create ha-retroarch --public --source=. --remote=origin --push
gh repo edit --add-topic home-assistant --add-topic hacs --add-topic retroarch --add-topic integration --add-topic libretro
```

- [ ] **Step 7: Verify CI passes**

Run: `gh run watch` (or check the Actions tab).
Expected: `Validate` (hassfest + hacs) and `Tests` jobs green.

---

## Task 17: Local hassfest sanity check + final full run

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite with coverage**

Run: `python -m pytest --cov=custom_components.retroarch -q`
Expected: all tests pass; coverage report prints.

- [ ] **Step 2: Manual JSON validation**

Run: `python -c "import json; [json.load(open(f)) for f in ['custom_components/retroarch/manifest.json','custom_components/retroarch/strings.json','custom_components/retroarch/translations/en.json','custom_components/retroarch/translations/pt-BR.json','hacs.json']]; print('JSON OK')"`
Expected: `JSON OK`

- [ ] **Step 3: Confirm manifest key order**

Read `manifest.json` and confirm key order is `domain`, `name`, then alphabetical (`codeowners`, `config_flow`, `documentation`, `integration_type`, `iot_class`, `issue_tracker`, `requirements`, `version`). Fix if hassfest CI flagged it.

- [ ] **Step 4: Final commit (if any fixes were made)**

```bash
git add -A
git commit -m "fix: address hassfest/HACS validation feedback"
git push
```

---

## Self-Review

**1. Spec coverage (user wanted "max sensors, actions, everything"):**
- Sensors: status, game, system, crc32, version, + unlimited user RAM sensors — Task 9. ✅
- Binary sensors: playing, paused, content_loaded — Task 10. ✅
- media_player with play/pause/stop/volume — Task 13. ✅
- Buttons: every fire-and-forget command from the protocol reference — Task 11. ✅
- Switches: optimistic toggles (fast forward, slow motion, mute, fullscreen, pause) — Task 12. ✅
- Services: send_command, read_memory (response), write_memory, show_message, load_state_slot, set_shader, load_core — Task 14. ✅
- RAM read/write — Tasks 4, 9, 14. ✅
- HACS + CI (hassfest + HACS validate) — Task 16. ✅
- Config flow + Options flow — Tasks 7, 15. ✅
- Auto-discovery: active LAN broadcast `VERSION` probe in the config flow, with manual fallback — Tasks 4b, 7. ✅ (Note: RetroArch has no mDNS/SSDP advertise, so HA passive discovery is impossible; active probing is the only option.)

**2. Placeholder scan:** Two intentional editing-artifact lines were called out and given corrected final file contents (Task 11 Step 1, Task 14 Step 1). No `TODO`/`implement later`/"add error handling" placeholders remain. ✅

**3. Type consistency:**
- `RetroArchClient` methods (`send_command`, `query`, `async_get_status`, `async_get_version`, `async_read_memory`, `async_write_memory`, `close`) are used consistently across coordinator, entities, and services. ✅
- `RetroArchStatus` fields (`available`, `state`, `system`, `game`, `crc32`, `version`, `ram`) match every consumer. ✅
- `coordinator.client`, `coordinator.device_name`, `coordinator.config_entry`, `coordinator.ram_sensors` referenced uniformly. ✅
- `entry.runtime_data` (the coordinator) used identically in `__init__.py`, all platforms, and services. ✅
- State constants (`STATE_PLAYING`, `STATE_PAUSED`, `STATE_CONTENTLESS`, `STATE_UNKNOWN`) shared via `const.py`. ✅
- Command strings: buttons/switches embed literals that match the protocol reference; `const.py` holds the ones reused in `api.py`. ✅

**Known follow-ups (out of scope for v1, documented for later):**
- Brands/icons PR to `home-assistant/brands` (HACS install works without it; missing logo is a warning, not a blocker).
- `GET_CONFIG_PARAM`-based diagnostic sensors (e.g. current video driver) could be added later.
- `READ_CORE_MEMORY` (achievement-address variant) as an alternative to `READ_CORE_RAM` for cores that support it.
