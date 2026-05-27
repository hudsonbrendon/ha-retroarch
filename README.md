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
- **Box art** — the media player shows the game's cover from the libretro thumbnail server (best-effort by system + ROM name; override the system folder or disable it in the Options flow).
- **Diagnostic config sensors** — video/audio/menu driver, read via `GET_CONFIG_PARAM`.
- **Reconfigure** — change host/port from the integration's ⋮ menu without removing it.
- **Diagnostics** — downloadable config-entry diagnostics (host redacted).

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
