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
  name, with play/pause/stop, **real volume level and mute** (read from RetroArch's
  `audio_volume` / `audio_mute_enable`), volume up/down, and a best-effort session
  play-time position.
- 🖼️ **Box art** — the media player shows the game's cover from the libretro thumbnail
  server (best-effort by system + ROM name; override the system folder or disable it in
  the options).
- 📊 **Sensors** — status, current game, system/core, content CRC32, RetroArch version,
  plus diagnostic config sensors (drivers, fast-forward/slow-motion ratios, RetroAchievements username).
- 🧠 **Configurable RAM sensors** — read live in-game values (lives, score, HP…) by
  memory address via the options flow, using either `READ_CORE_RAM` or the wider-support
  **system memory map** (`READ_CORE_MEMORY`).
- 🔘 **Binary sensors** — playing, paused, content-loaded, menu open, replay active, and RetroAchievements (normal + hardcore).
- 🕹️ **Buttons** — 50+ control commands: reset, pause/resume, save/load state, state
  slot ±, screenshot, fast forward, rewind, slow motion, AI service, menu, close content,
  quit, disk eject/next/prev, shader next/prev/toggle, cheat toggle/index ±, volume ±,
  recording/streaming toggle, FPS/statistics/game-focus/grab-mouse/run-ahead/VRR/preempt/turbo/desktop-menu toggles,
  **SRAM save/load to disk**, **menu navigation** (up/down/left/right/confirm/back, OSK, overlay),
  full **replay** controls, and **netplay** toggles.
- 🎚️ **Switches** — fullscreen, pause, and **mute** reflect RetroArch's real state; fast forward and slow motion are optimistic (the protocol only toggles them).
- 🔢 **Number** — pick the active save-state slot directly (steps to the target slot).
- ⬆️ **Update** — shows when a newer RetroArch release is published on GitHub (informational).
- 📡 **Events** — fires `retroarch_game_started`, `retroarch_game_stopped`, and
  `retroarch_game_changed` on the HA event bus for automations.
- 🛠️ **Services** — `send_command`, `read_memory` / `read_memory_map` (return data),
  `write_memory` / `write_memory_map`, `save_files`, `load_files`, `show_message`,
  `load_state_slot`, `play_replay_slot`, `set_shader`, and `load_core`.
- 🔍 **Auto-discovery** — finds RetroArch instances on your LAN via a UDP `VERSION`
  broadcast probe, with manual host/port entry as a fallback.
- 🩺 **Diagnostics** — netplay nickname and RetroArch directory sensors (disabled by
  default) plus downloadable config-entry diagnostics.
- 🏠 **Local polling** — no cloud; talks straight to RetroArch on your network.
- 🌐 **Localized** — UI, entities, and services translated to English, Português (Brasil), and Español.

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
| `media_player.retroarch` | State (playing / paused / idle), game as `media_title`, system as `app_name`, box art, play/pause/stop, real `volume_level` / `is_volume_muted`, volume ±, and session play-time as `media_position`. |

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.retroarch_status` | `playing` / `paused` / `contentless` / `unknown` |
| `sensor.retroarch_game` | Current game (content basename) |
| `sensor.retroarch_system` | Current system / core |
| `sensor.retroarch_content_crc32` | Content CRC32 (diagnostic) |
| `sensor.retroarch_version` | RetroArch version (diagnostic) |
| `sensor.retroarch_netplay_nickname` + directory sensors | Netplay nickname and save/state/system/cache/log directories via `GET_CONFIG_PARAM` (diagnostic, disabled by default) |
| Driver / ratio / cheevos diagnostic sensors | Video/audio/input driver, fast-forward & slow-motion ratios, RetroAchievements username via `GET_CONFIG_PARAM` (diagnostic, disabled by default) |
| `sensor.retroarch_<name>` | One per configured RAM sensor |

### Binary sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.retroarch_playing` | On while a game is running |
| `binary_sensor.retroarch_paused` | On while paused |
| `binary_sensor.retroarch_content_loaded` | On when content is loaded (diagnostic) |
| `binary_sensor.retroarch_menu_open` | On while the RetroArch menu is open |
| `binary_sensor.retroarch_replay_active` | On while a replay is recording/playing |
| `binary_sensor.retroarch_retroachievements` | On when RetroAchievements is enabled (diagnostic) |
| `binary_sensor.retroarch_retroachievements_hardcore` | On when RetroAchievements hardcore mode is enabled (diagnostic) |

### Switches

Fast forward · Slow motion · Mute · Fullscreen · Pause.

> **Fullscreen**, **Pause**, and **Mute** reflect RetroArch's real state (read from
> `video_fullscreen`, the play/pause status, and `audio_mute_enable`). **Fast forward**
> and **Slow motion** are optimistic — RetroArch only exposes *toggle* commands for them
> and doesn't report their state, so they send a command only when the requested state
> differs from the assumed one.

### Number

`number.retroarch_state_slot` — sets the active save-state slot. RetroArch has no
"set slot" command, so the entity steps `STATE_SLOT_PLUS` / `STATE_SLOT_MINUS` from the
current slot to the target.

### Update

`update.retroarch_retroarch` — compares the running version with the latest
`libretro/RetroArch` GitHub release (checked at startup and every 12 h). Informational
only; it can't install updates over the network.

### Buttons

Reset · Pause/Resume · Frame advance · Save/Load state · State slot ± · Screenshot ·
Fast forward · Rewind · Slow motion · AI service · Menu · Close content · Quit ·
Disk eject/next/prev · Shader next/prev/toggle · Cheat toggle/index ± · Volume ± ·
Recording/Streaming toggle · FPS/Statistics/Game-focus/Grab-mouse/Run-ahead/VRR/Preempt/Turbo-fire/Desktop-menu toggles ·
Save/Load SRAM to disk · Menu up/down/left/right/confirm/back · On-screen keyboard · Next overlay ·
Play/Record/Halt replay · Replay slot ± · Save/Prev/Next replay checkpoint ·
Netplay host/ping/spectate/player-chat/fade-chat toggles.

## Services

| Service | Description |
|---------|-------------|
| `retroarch.send_command` | Send any raw Network Control command. |
| `retroarch.read_memory` | Read core RAM (`READ_CORE_RAM`) at a hex address; returns the bytes. |
| `retroarch.write_memory` | Write bytes to core RAM (`WRITE_CORE_RAM`) at a hex address. |
| `retroarch.read_memory_map` | Read via the core's system memory map (`READ_CORE_MEMORY`); returns the bytes. |
| `retroarch.write_memory_map` | Write via the core's system memory map (`WRITE_CORE_MEMORY`). |
| `retroarch.save_files` | Flush all SRAM (battery saves) to disk. |
| `retroarch.load_files` | Reload all SRAM (battery saves) from disk. |
| `retroarch.show_message` | Show an on-screen message. |
| `retroarch.load_state_slot` | Load a specific save-state slot. |
| `retroarch.play_replay_slot` | Play the replay in a specific slot. |
| `retroarch.set_shader` | Load a shader by path. |
| `retroarch.load_core` | Load a core by path. |

## Events

The integration fires these on the Home Assistant event bus (use them as automation triggers):

| Event | Data |
|-------|------|
| `retroarch_game_started` | `entry_id`, `device`, `game`, `system` |
| `retroarch_game_changed` | `entry_id`, `device`, `game`, `system`, `previous_game` |
| `retroarch_game_stopped` | `entry_id`, `device`, `game` |

## RAM sensors

**Settings → Devices & Services → RetroArch → Configure → Add a RAM sensor.** Provide a
name, hex address (e.g. `7e0019`), byte count, and optional signed / big-endian / scale /
unit. Tick **Use system memory map** to read via `READ_CORE_MEMORY` (the system bus
address space, supported by more cores) instead of `READ_CORE_RAM` — note the two use
different address spaces, so pick the one your memory map targets. Addresses are
core-specific — consult RetroAchievements memory maps or cheat files for your game.

## Box art

Box art is best-effort: `GET_STATUS` only gives a short system id and the ROM basename,
while the libretro thumbnail server is keyed by full system folder + playlist label. It
works well for No-Intro / Redump-named ROMs on mapped systems. If it misses, set the exact
libretro system folder (e.g. `Nintendo - Super Nintendo Entertainment System`) or disable
it under **Configure → Box art**.

## Cookbook

A few automation ideas using the entities and events above.

**Pause when you leave the room**

```yaml
automation:
  - alias: Pause RetroArch when the room empties
    trigger:
      - trigger: state
        entity_id: binary_sensor.living_room_presence
        to: "off"
    condition:
      - condition: state
        entity_id: binary_sensor.retroarch_playing
        state: "on"
    action:
      - action: switch.turn_on
        target:
          entity_id: switch.retroarch_pause
```

**Game-night scene when a game starts**

```yaml
automation:
  - alias: Game night lights
    trigger:
      - trigger: event
        event_type: retroarch_game_started
    action:
      - action: scene.turn_on
        target:
          entity_id: scene.game_night
```

**Back up SRAM every night**

```yaml
automation:
  - alias: Nightly SRAM backup
    trigger:
      - trigger: time
        at: "03:00:00"
    action:
      - action: retroarch.save_files
        data:
          config_entry_id: <your entry id>
```

**Now-playing notification**

```yaml
automation:
  - alias: Announce the current game
    trigger:
      - trigger: event
        event_type: retroarch_game_changed
    action:
      - action: notify.mobile_app
        data:
          message: "Now playing {{ trigger.event.data.game }} ({{ trigger.event.data.system }})"
```

## Notes & limitations

- The Network Control Interface only **toggles** fast forward / slow motion and doesn't
  report their state, so those switches are optimistic. Mute, fullscreen, and pause now
  read real state.
- `read_memory` / `write_memory` use `READ_CORE_RAM`; `read_memory_map` / `write_memory_map`
  use `READ_CORE_MEMORY` (system memory map). Support and the address space depend on the
  loaded core.
- Launching arbitrary games isn't possible (there's no stable "load content" command), but
  the **menu navigation** buttons let an automation drive the RetroArch menu to load a
  playlist entry. Screenshots can be triggered but not retrieved over the network.

## License

[MIT](LICENSE)
