# RetroArch Integration v0.2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add box art on the media_player, diagnostic config-param sensors, a reconfigure flow, and config-entry diagnostics to the existing `retroarch` integration.

**Architecture:** Extend the existing UDP client (`GET_CONFIG_PARAM`), carry new fields on `RetroArchStatus` (`config`), add a pure `thumbnails.py` helper for libretro box-art URLs, surface box art via `media_player.media_image_url` (HA fetches/caches server-side, so 404s degrade gracefully), add box-art options to the OptionsFlow, add a reconfigure step to the config flow, and add `diagnostics.py`.

**Tech Stack:** Same as v0.1.0 — Home Assistant, asyncio UDP, pytest + pytest-homeassistant-custom-component. No new runtime deps.

**Baseline:** All v0.1.0 code exists and 47 tests pass. Work from `/Users/hudsonbrendon/Github/ha-retroarch`, use `.venv/bin/python`. Commits: author solely Hudson Brendon, NO Co-Authored-By trailer. Each platform/full-setup test patches `PLATFORMS` to the platform(s) under test (or `[]`), per the v0.1.0 convention.

---

## Task 1: GET_CONFIG_PARAM — client method + status field

**Files:** Modify `api.py`, Modify `tests/test_api.py`.

- [ ] **Step 1: Append failing tests to `tests/test_api.py`**

```python
async def test_get_config_param_parses_value():
    client, _ = _wire_client(b"GET_CONFIG_PARAM video_driver gl")
    assert await client.async_get_config_param("video_driver") == "gl"


async def test_get_config_param_none_on_timeout():
    client, _ = _wire_client(None)
    assert await client.async_get_config_param("video_driver") is None
```

- [ ] **Step 2: Run — expect FAIL** (`async_get_config_param` missing)

Run: `.venv/bin/python -m pytest tests/test_api.py -q`

- [ ] **Step 3: Edit `api.py`**

Add `CMD_GET_CONFIG_PARAM` to the `from .const import (...)` block (alphabetical position, next to `CMD_GET_STATUS`). Re-add the constant in `const.py` first (see note). Then add this method to `RetroArchClient` (after `async_get_status`):

```python
    async def async_get_config_param(self, name: str) -> str | None:
        """Return a retroarch.cfg parameter value, or None if unavailable."""
        response = await self.query(f"{CMD_GET_CONFIG_PARAM} {name}")
        if not response:
            return None
        # Response: "GET_CONFIG_PARAM <name> <value>"
        prefix = f"{CMD_GET_CONFIG_PARAM} {name} "
        if response.startswith(prefix):
            return response[len(prefix):].strip() or None
        return None
```

In `const.py`, re-add (it was removed in v0.1.0 cleanup) under the status/info commands section:
```python
CMD_GET_CONFIG_PARAM: Final = "GET_CONFIG_PARAM"
```

Also add a `config` field to `RetroArchStatus` (in `api.py`), after `ram`:
```python
    config: dict[str, str] = field(default_factory=dict)
```

- [ ] **Step 4: Run — expect PASS** (`tests/test_api.py` all green)

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/api.py custom_components/retroarch/const.py tests/test_api.py
git commit -m "feat: add GET_CONFIG_PARAM client method and status.config field"
```

---

## Task 2: Coordinator fetches config params (cached)

**Files:** Modify `coordinator.py`, Modify `tests/test_coordinator.py`.

- [ ] **Step 1: Append failing test to `tests/test_coordinator.py`**

```python
async def test_coordinator_fetches_config_once(hass):
    client = AsyncMock()
    client.async_get_status.return_value = RetroArchStatus(available=True, state="playing")
    client.async_get_version.return_value = "1.19.1"
    client.async_get_config_param.side_effect = lambda name: {
        "video_driver": "gl",
        "audio_driver": "alsa",
        "menu_driver": "ozone",
    }.get(name)

    coordinator = RetroArchDataUpdateCoordinator(
        hass, client=client, name="RetroArch", scan_interval=5, ram_sensors=[]
    )

    data = await coordinator._async_update_data()
    assert data.config["video_driver"] == "gl"
    assert data.config["menu_driver"] == "ozone"

    # second refresh must not re-query config (cached)
    client.async_get_config_param.reset_mock()
    await coordinator._async_update_data()
    client.async_get_config_param.assert_not_called()
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Edit `coordinator.py`**

Add a module-level constant after the imports:
```python
CONFIG_PARAMS: tuple[str, ...] = ("video_driver", "audio_driver", "menu_driver")
```
In `__init__`, add `self._config: dict[str, str] | None = None` next to `self._version`.
In `_async_update_data`, after the version block and before the RAM loop, add:
```python
        if self._config is None:
            self._config = {}
            for param in CONFIG_PARAMS:
                value = await self.client.async_get_config_param(param)
                if value is not None:
                    self._config[param] = value
        status.config = self._config
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/coordinator.py tests/test_coordinator.py
git commit -m "feat: coordinator caches diagnostic config params"
```

---

## Task 3: Config-param diagnostic sensors

**Files:** Modify `sensor.py`, Modify `tests/test_sensor.py`.

- [ ] **Step 1: Append failing test to `tests/test_sensor.py`**

```python
async def test_config_param_sensor(hass):
    status = RetroArchStatus(
        available=True, state="playing", system="nes", game="Metroid",
        config={"video_driver": "gl", "audio_driver": "alsa", "menu_driver": "ozone"},
    )
    await _setup(hass, status)
    state = hass.states.get("sensor.retroarch_video_driver")
    assert state.state == "gl"
```

The existing `_setup` patches `async_read_memory`; also patch `async_get_config_param` so the coordinator's first-poll config fetch returns the same values. Update `_setup` to add, inside its `with patch(...)` chain:
```python
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=AsyncMock(side_effect=lambda name: status.config.get(name)),
    ):
```
(So the coordinator populates `data.config` from the same dict the test asserts.)

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Edit `sensor.py`**

Add config-param sensor descriptions and entities. After `STATUS_SENSORS`, add:
```python
CONFIG_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="video_driver",
        name="Video driver",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="audio_driver",
        name="Audio driver",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="menu_driver",
        name="Menu driver",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)
```
In `async_setup_entry`, after appending RAM sensors, add:
```python
    entities.extend(
        RetroArchConfigSensor(coordinator, description) for description in CONFIG_SENSORS
    )
```
Add the entity class (after `RetroArchSensor`):
```python
class RetroArchConfigSensor(RetroArchEntity, SensorEntity):
    """A diagnostic sensor reading a cached retroarch.cfg parameter."""

    def __init__(
        self,
        coordinator: RetroArchDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_cfg_{description.key}"

    @property
    def native_value(self) -> StateType:
        return self.coordinator.data.config.get(self.entity_description.key)
```

- [ ] **Step 4: Run — expect PASS** (`sensor.retroarch_video_driver` is enabled in the test even though `entity_registry_enabled_default=False`, because newly added entities are still created in state during setup in tests; if the test finds the state is missing because the entity is registry-disabled, set `entity_registry_enabled_default=True` on the three descriptions instead.)

> Implementer note: registry-disabled entities are NOT added to `hass.states` in tests. So for these three sensors, use `entity_registry_enabled_default=True` (drop the `entity_registry_enabled_default=False` lines above) so they appear by default and the test passes. Diagnostic category already keeps them out of the way.

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/sensor.py tests/test_sensor.py
git commit -m "feat: add diagnostic config-param sensors (drivers)"
```

---

## Task 4: Box art — thumbnails helper

**Files:** Create `custom_components/retroarch/thumbnails.py`, Create `tests/test_thumbnails.py`.

- [ ] **Step 1: Write `tests/test_thumbnails.py`**

```python
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
```

- [ ] **Step 2: Run — expect FAIL** (module missing)

- [ ] **Step 3: Write `custom_components/retroarch/thumbnails.py`**

```python
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
    return (
        f"{THUMBNAIL_BASE}/{quote(folder)}/Named_Boxarts/{quote(sanitize(game))}.png"
    )
```

> Note on `sanitize` test: spaces are preserved; `quote()` later encodes spaces as `%20`. `quote` default does NOT encode `/` but our folder/game segments are quoted individually so embedded `/` in a name would be encoded — acceptable.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/thumbnails.py tests/test_thumbnails.py
git commit -m "feat: add libretro box-art URL helper"
```

---

## Task 5: Box art on media_player + options

**Files:** Modify `const.py`, Modify `media_player.py`, Modify `config_flow.py`, Modify `strings.json` + `translations/en.json` + `translations/pt-BR.json`, Modify `tests/test_media_player.py`, Modify `tests/test_config_flow.py`.

- [ ] **Step 1: Add option keys to `const.py`**

After the RAM sensor keys:
```python
CONF_BOX_ART_ENABLED: Final = "box_art_enabled"
CONF_BOX_ART_SYSTEM: Final = "box_art_system"
```

- [ ] **Step 2: Append failing test to `tests/test_media_player.py`**

```python
from custom_components.retroarch.const import CONF_BOX_ART_ENABLED, CONF_BOX_ART_SYSTEM


async def _setup_with_options(hass, status, options):
    from homeassistant.const import Platform
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, options=options, unique_id="192.168.1.50:55355"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", [Platform.MEDIA_PLAYER]), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=status),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=AsyncMock(return_value=None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_media_image_url_known_system(hass):
    status = RetroArchStatus(available=True, state="playing", system="super_nintendo", game="Super Mario World (USA)")
    await _setup_with_options(hass, status, {CONF_BOX_ART_ENABLED: True})
    state = hass.states.get("media_player.retroarch")
    pic = state.attributes.get("entity_picture", "")
    # entity_picture is a proxied URL; just assert media image is exposed
    assert pic  # non-empty proxy URL means media_image_url resolved


async def test_media_image_disabled(hass):
    status = RetroArchStatus(available=True, state="playing", system="super_nintendo", game="Super Mario World (USA)")
    await _setup_with_options(hass, status, {CONF_BOX_ART_ENABLED: False})
    state = hass.states.get("media_player.retroarch")
    assert "entity_picture" not in state.attributes
```

> Note: when `media_image_url` is set, HA exposes a proxied `entity_picture` attribute. The first test asserts it's present; the second asserts it's absent when box art is disabled.

- [ ] **Step 3: Run — expect FAIL**

- [ ] **Step 4: Edit `media_player.py`**

Add import:
```python
from .const import CONF_BOX_ART_ENABLED, CONF_BOX_ART_SYSTEM, STATE_PAUSED, STATE_PLAYING
from .thumbnails import boxart_url
```
(Replace the existing `from .const import STATE_PAUSED, STATE_PLAYING` line.)

Add a `media_image_url` property to `RetroArchMediaPlayer`:
```python
    @property
    def media_image_url(self) -> str | None:
        options = self.coordinator.config_entry.options
        if not options.get(CONF_BOX_ART_ENABLED, True):
            return None
        data = self.coordinator.data
        return boxart_url(data.system, data.game, options.get(CONF_BOX_ART_SYSTEM) or None)
```

- [ ] **Step 5: Add a box-art options step to `config_flow.py`**

Add the new const imports to the existing `from .const import (...)` block: `CONF_BOX_ART_ENABLED`, `CONF_BOX_ART_SYSTEM`.

In `RetroArchOptionsFlow.async_step_init`, add `"box_art"` to `menu_options`:
```python
            menu_options=["settings", "box_art", "add_ram_sensor", "remove_ram_sensor"],
```
Add the step method:
```python
    async def async_step_box_art(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(
                {
                    CONF_BOX_ART_ENABLED: user_input[CONF_BOX_ART_ENABLED],
                    CONF_BOX_ART_SYSTEM: user_input.get(CONF_BOX_ART_SYSTEM, ""),
                }
            )

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BOX_ART_ENABLED,
                    default=options.get(CONF_BOX_ART_ENABLED, True),
                ): bool,
                vol.Optional(
                    CONF_BOX_ART_SYSTEM,
                    default=options.get(CONF_BOX_ART_SYSTEM, ""),
                ): str,
            }
        )
        return self.async_show_form(step_id="box_art", data_schema=schema)
```

- [ ] **Step 6: Add strings for the box_art step**

In `strings.json` AND `translations/en.json`, under `options` → `step`, add `box_art` and add it to `init.menu_options`:
```json
        "menu_options": {
          "settings": "Polling settings",
          "box_art": "Box art",
          "add_ram_sensor": "Add a RAM sensor",
          "remove_ram_sensor": "Remove a RAM sensor"
        }
```
and a new step block:
```json
      "box_art": {
        "title": "Box art",
        "data": {
          "box_art_enabled": "Show box art on the media player",
          "box_art_system": "Override libretro system folder (optional, e.g. Nintendo - Super Nintendo Entertainment System)"
        }
      },
```
In `translations/pt-BR.json`, same structure:
```json
        "menu_options": {
          "settings": "Configurações de polling",
          "box_art": "Capa do jogo",
          "add_ram_sensor": "Adicionar sensor de RAM",
          "remove_ram_sensor": "Remover sensor de RAM"
        }
```
```json
      "box_art": {
        "title": "Capa do jogo",
        "data": {
          "box_art_enabled": "Mostrar a capa no media player",
          "box_art_system": "Sobrescrever a pasta de sistema do libretro (opcional, ex.: Nintendo - Super Nintendo Entertainment System)"
        }
      },
```
Keep `strings.json` and `translations/en.json` byte-identical; verify with `diff`.

- [ ] **Step 7: Append an options test to `tests/test_config_flow.py`**

```python
from custom_components.retroarch.const import CONF_BOX_ART_ENABLED


async def test_options_box_art(hass):
    entry = await _load_entry(hass)
    with patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "box_art"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"box_art_enabled": False, "box_art_system": ""}
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_BOX_ART_ENABLED] is False
```

> The existing `_load_entry` does a full setup; the coordinator now calls `async_get_config_param`, so patch it (returning None) wherever `_load_entry` is used in newly added tests, as shown.

- [ ] **Step 8: Run the affected suites — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_media_player.py tests/test_config_flow.py -q`

- [ ] **Step 9: Commit**

```bash
git add custom_components/retroarch/const.py custom_components/retroarch/media_player.py custom_components/retroarch/config_flow.py custom_components/retroarch/strings.json custom_components/retroarch/translations tests/test_media_player.py tests/test_config_flow.py
git commit -m "feat: box art on media_player with options override"
```

---

## Task 6: Reconfigure flow

**Files:** Modify `config_flow.py`, Modify `strings.json` + `translations/en.json` + `translations/pt-BR.json`, Modify `tests/test_config_flow.py`.

- [ ] **Step 1: Append failing test to `tests/test_config_flow.py`**

```python
from homeassistant.const import CONF_HOST


async def test_reconfigure_updates_host(hass):
    entry = await _load_entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.retroarch.config_flow.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=_AsyncMock(return_value=RetroArchStatus(available=True, state="contentless")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=_AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=_AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "192.168.1.99", "port": 55355, "name": "RetroArch"},
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "192.168.1.99"
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Add the reconfigure step to `RetroArchConfigFlow`** (in `config_flow.py`, after `async_step_manual`)

```python
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change host/port/name of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            if await self._async_reachable(user_input):
                return self.async_update_reload_and_abort(entry, data=user_input)
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, entry.data),
            errors=errors,
        )
```

- [ ] **Step 4: Add strings**

In `strings.json` AND `translations/en.json`, under `config` → `step`, add a `reconfigure` block (same fields as `manual`):
```json
      "reconfigure": {
        "title": "Reconfigure RetroArch",
        "description": "Update the host and port of this RetroArch instance.",
        "data": {
          "host": "Host",
          "port": "Port",
          "name": "Name"
        }
      },
```
Under `config` → `abort`, add:
```json
        "reconfigure_successful": "RetroArch reconfigured successfully."
```
In `translations/pt-BR.json`, under `config` → `step` add:
```json
      "reconfigure": {
        "title": "Reconfigurar RetroArch",
        "description": "Atualize o host e a porta desta instância do RetroArch.",
        "data": {
          "host": "Host",
          "port": "Porta",
          "name": "Nome"
        }
      },
```
and under `config` → `abort`:
```json
        "reconfigure_successful": "RetroArch reconfigurado com sucesso."
```
Keep `strings.json` == `translations/en.json` (verify with `diff`).

- [ ] **Step 5: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_config_flow.py -q`

- [ ] **Step 6: Commit**

```bash
git add custom_components/retroarch/config_flow.py custom_components/retroarch/strings.json custom_components/retroarch/translations tests/test_config_flow.py
git commit -m "feat: add reconfigure flow"
```

---

## Task 7: Config-entry diagnostics

**Files:** Create `custom_components/retroarch/diagnostics.py`, Create `tests/test_diagnostics.py`.

- [ ] **Step 1: Write `tests/test_diagnostics.py`**

```python
"""Tests for RetroArch diagnostics."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.retroarch.api import RetroArchStatus
from custom_components.retroarch.const import DOMAIN
from custom_components.retroarch.diagnostics import async_get_config_entry_diagnostics

from .const import MOCK_CONFIG


async def test_diagnostics_redacts_host(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="192.168.1.50:55355")
    entry.add_to_hass(hass)
    with patch("custom_components.retroarch.PLATFORMS", []), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_status",
        new=AsyncMock(return_value=RetroArchStatus(available=True, state="playing", system="nes", game="Metroid")),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_version",
        new=AsyncMock(return_value="1.19.1"),
    ), patch(
        "custom_components.retroarch.coordinator.RetroArchClient.async_get_config_param",
        new=AsyncMock(return_value=None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["data"]["host"] == "**REDACTED**"
    assert diag["status"]["game"] == "Metroid"
    assert diag["status"]["state"] == "playing"
```

- [ ] **Step 2: Run — expect FAIL** (module missing)

- [ ] **Step 3: Write `custom_components/retroarch/diagnostics.py`**

```python
"""Diagnostics support for RetroArch."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import RetroArchConfigEntry

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RetroArchConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "status": {
            "available": data.available,
            "state": data.state,
            "system": data.system,
            "game": data.game,
            "crc32": data.crc32,
            "version": data.version,
            "config": data.config,
            "ram_keys": list(data.ram),
        },
    }
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add custom_components/retroarch/diagnostics.py tests/test_diagnostics.py
git commit -m "feat: add config entry diagnostics"
```

---

## Task 8: Version bump, README, full suite, release

**Files:** Modify `manifest.json`, Modify `README.md`.

- [ ] **Step 1: Bump version in `manifest.json`** — change `"version": "0.1.0"` to `"version": "0.2.0"`. Keep key order intact.

- [ ] **Step 2: Update `README.md` Features** — add bullets:
```markdown
- **Box art** — media player shows the game's cover from the libretro thumbnail server (best-effort by system + ROM name; override the system folder or disable it in the Options flow).
- **Diagnostic config sensors** — video/audio/menu driver, read via GET_CONFIG_PARAM.
- **Reconfigure** — change host/port from the integration's ⋮ menu without removing it.
- **Diagnostics** — downloadable config-entry diagnostics (host redacted).
```

- [ ] **Step 3: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (47 baseline + the new tests).

- [ ] **Step 4: Validate JSON + en==strings**

```bash
.venv/bin/python -c "import json; [json.load(open(f)) for f in ['custom_components/retroarch/manifest.json','custom_components/retroarch/strings.json','custom_components/retroarch/translations/en.json','custom_components/retroarch/translations/pt-BR.json','hacs.json']]; print('JSON OK')"
diff custom_components/retroarch/strings.json custom_components/retroarch/translations/en.json && echo "en==strings"
```

- [ ] **Step 5: Commit + push + release** (push/release are user-authorized for this project)

```bash
git add custom_components/retroarch/manifest.json README.md
git commit -m "chore: bump to v0.2.0 and update README"
git push origin main
```
Then create the release:
```bash
gh release create v0.2.0 --repo hudsonbrendon/ha-retroarch --target main --title "v0.2.0" --notes "Box art on the media player, diagnostic config sensors (drivers), reconfigure flow, and config-entry diagnostics."
```
Then confirm CI is green (`gh run list`).

---

## Self-Review

**Spec coverage:** Box art (Tasks 4–5) with options override ✅; GET_CONFIG_PARAM sensors (Tasks 1–3) ✅; reconfigure (Task 6) ✅; diagnostics (Task 7) ✅; repair issue intentionally excluded (undetectable over UDP — documented). Version/README/release (Task 8) ✅.

**Type consistency:** `RetroArchStatus.config` added in Task 1 and consumed in Tasks 2/3/7; `async_get_config_param` used in coordinator + patched in every full-setup test (media_player, config_flow, diagnostics) so the new coordinator fetch doesn't break existing setups; `boxart_url(system, game, override)` signature consistent between Task 4 and Task 5; option keys `CONF_BOX_ART_ENABLED`/`CONF_BOX_ART_SYSTEM` consistent across const/media_player/config_flow.

**Gotchas baked in:** registry-disabled entities don't appear in test states (config sensors use `entity_registry_enabled_default=True`); every full-setup test added/touched here patches `async_get_config_param`; strings.json must stay byte-identical to en.json; manifest key order preserved on version bump.
