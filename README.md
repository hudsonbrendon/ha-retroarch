<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/retroarch/brand/dark_logo.png">
    <img src="custom_components/retroarch/brand/logo.png" alt="RetroArch" width="420">
  </picture>
</p>

# RetroArch for Home Assistant

[![Tests](https://github.com/hudsonbrendon/ha-retroarch/actions/workflows/tests.yaml/badge.svg)](https://github.com/hudsonbrendon/ha-retroarch/actions/workflows/tests.yaml)
[![Validate](https://github.com/hudsonbrendon/ha-retroarch/actions/workflows/validate.yaml/badge.svg)](https://github.com/hudsonbrendon/ha-retroarch/actions/workflows/validate.yaml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/ha-retroarch)](https://github.com/hudsonbrendon/ha-retroarch/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Monitor and control a [**RetroArch**](https://www.retroarch.com/) instance from Home
Assistant over its UDP **Network Control Interface** — the running game and system,
play/pause/reset/save-state and dozens of other commands, optimistic toggles, live RAM
values, box art, and LAN auto-discovery.

> Talks to RetroArch's Network Control Interface over UDP (default port `55355`).
> Everything runs on your LAN — no cloud, no account. Not affiliated with the
> libretro / RetroArch project.

## Features

- 🎮 **Media player** — the running game as the media title, the system/core as the app
  name, with play/pause/stop and volume up/down/mute.
- 🖼️ **Box art** — the media player shows the game's cover from the libretro thumbnail
  server (best-effort by system + ROM name; override the system folder or disable it in
  the options).
- 📊 **Sensors** — status, current game, system/core, content CRC32, and RetroArch version.
- 🧠 **Configurable RAM sensors** — read live in-game values (lives, score, HP…) by
  memory address via the options flow.
- 🔘 **Binary sensors** — playing, paused, and content-loaded.
- 🕹️ **Buttons** — 34 control commands: reset, pause/resume, save/load state, state
  slot ±, screenshot, fast forward, rewind, slow motion, AI service, menu, close content,
  quit, disk eject/next/prev, shader next/prev/toggle, cheat toggle/index ±, volume ±,
  recording/streaming toggle, and FPS/statistics/game-focus/grab-mouse/run-ahead/VRR toggles.
- 🎚️ **Switches** (optimistic) — fast forward, slow motion, mute, fullscreen, and pause.
- 🛠️ **Services** — `send_command`, `read_memory` (returns data), `write_memory`,
  `show_message`, `load_state_slot`, `set_shader`, and `load_core`.
- 🔍 **Auto-discovery** — finds RetroArch instances on your LAN via a UDP `VERSION`
  broadcast probe, with manual host/port entry as a fallback.
- 🩺 **Diagnostics** — driver sensors (video/audio/menu) plus downloadable config-entry
  diagnostics.
- 🏠 **Local polling** — no cloud; talks straight to RetroArch on your network.

## Requirements

- Home Assistant **2024.12** or newer.
- A RetroArch instance reachable on your network with the **Network Control Interface
  enabled**.

Enable it in RetroArch via **Settings → Network → Network Commands** (and confirm
**Network Command Port** = `55355`), or in `retroarch.cfg`:

```
network_cmd_enable = "true"
network_cmd_port = "55355"
```

Restart RetroArch afterwards. Auto-discovery uses a LAN broadcast, so it works best when
Home Assistant and RetroArch are on the same subnet.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hudsonbrendon&repository=ha-retroarch&category=integration)

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Add `https://github.com/hudsonbrendon/ha-retroarch` and choose the **Integration**
   category — or use the button above.
3. Search for **RetroArch** in HACS, install it, and **restart Home Assistant**.

### Manual

1. Copy `custom_components/retroarch/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Add Integration → RetroArch**.
2. Choose **Search the network automatically** to pick a discovered instance, or
   **Enter connection details manually** to type the host and port.

You can later change the host/port without removing the integration via **Configure**
(reconfigure flow).

## Entities

### Media player

| Entity | Notes |
|--------|-------|
| `media_player.retroarch` | State (playing / paused / idle), game as `media_title`, system as `app_name`, box art, play/pause/stop, volume ± / mute. |

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.retroarch_status` | `playing` / `paused` / `contentless` / `unknown` |
| `sensor.retroarch_game` | Current game (content basename) |
| `sensor.retroarch_system` | Current system / core |
| `sensor.retroarch_content_crc32` | Content CRC32 (diagnostic) |
| `sensor.retroarch_version` | RetroArch version (diagnostic) |
| `sensor.retroarch_video_driver` · `_audio_driver` · `_menu_driver` | Drivers via `GET_CONFIG_PARAM` (diagnostic) |
| `sensor.retroarch_<name>` | One per configured RAM sensor |

### Binary sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.retroarch_playing` | On while a game is running |
| `binary_sensor.retroarch_paused` | On while paused |
| `binary_sensor.retroarch_content_loaded` | On when content is loaded (diagnostic) |

### Switches (optimistic)

Fast forward · Slow motion · Mute · Fullscreen · Pause.

> RetroArch only exposes *toggle* commands and doesn't report these states, so a switch
> sends a command only when the requested state differs from its assumed state.

### Buttons

Reset · Pause/Resume · Frame advance · Save/Load state · State slot ± · Screenshot ·
Fast forward · Rewind · Slow motion · AI service · Menu · Close content · Quit ·
Disk eject/next/prev · Shader next/prev/toggle · Cheat toggle/index ± · Volume ± ·
Recording/Streaming toggle · FPS/Statistics/Game-focus/Grab-mouse/Run-ahead/VRR toggles.

## Services

| Service | Description |
|---------|-------------|
| `retroarch.send_command` | Send any raw Network Control command. |
| `retroarch.read_memory` | Read core RAM at a hex address; returns the bytes. |
| `retroarch.write_memory` | Write bytes to core RAM at a hex address. |
| `retroarch.show_message` | Show an on-screen message. |
| `retroarch.load_state_slot` | Load a specific save-state slot. |
| `retroarch.set_shader` | Load a shader by path. |
| `retroarch.load_core` | Load a core by path. |

## RAM sensors

**Settings → Devices & Services → RetroArch → Configure → Add a RAM sensor.** Provide a
name, hex address (e.g. `7e0019`), byte count, and optional signed / big-endian / scale /
unit. Addresses are core-specific — consult RetroAchievements memory maps or cheat files
for your game.

## Box art

Box art is best-effort: `GET_STATUS` only gives a short system id and the ROM basename,
while the libretro thumbnail server is keyed by full system folder + playlist label. It
works well for No-Intro / Redump-named ROMs on mapped systems. If it misses, set the exact
libretro system folder (e.g. `Nintendo - Super Nintendo Entertainment System`) or disable
it under **Configure → Box art**.

## Notes & limitations

- The Network Control Interface only **toggles** fast forward / mute / fullscreen and
  doesn't report their state, so those switches are optimistic.
- `read_memory` / `write_memory` use `READ_CORE_RAM` / `WRITE_CORE_RAM`; support depends
  on the loaded core.
- Launching arbitrary games isn't possible (there's no stable "load content" command), and
  screenshots can be triggered but not retrieved over the network.

## License

[MIT](LICENSE)
