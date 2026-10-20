"""The cast (reparto): who plays each role the 3D code knows how to stage, and what scripts call them.

The Blender code stages two roles, each in a fixed *slot* (an internal id the sets, cameras and rigs are built
around, ~90 places in blender/):
- "humano" (slot `novato`): the human lead (low-poly person: desk or counter, phone, tears, arms that type...).
- "cosa" (slot `claude`): the thing that notices (a mug, a desk lamp, a moka pot...).

Who *plays* each slot is data, not code: any character folder (`personajes/<id>/personaje.json`, or the template's
own `assets/characters/<id>/character.json`) of the right kind can fill it. The player's look, voice and subtitle
colour are used; the slot id stays internal. Resolution, per script (`resolve_script`):

1. `reparto.json` (project defaults): which character plays each role and the extra names scripts may use.
2. The script's own `"reparto": {"humano": "estudiante", "cosa": "lucio"}` (this episode only) wins over 1.
3. Otherwise the cast is inferred from `characters`: the first human listed fills "humano" and the first thing
   fills "cosa" (unless a role name, a slot id or an alias of that role is already listed).

Every name is then translated to internal ids (speaker, reactor, gaze, screen owners, role-named cameras...), and
the resolved `reparto` is written back into the script data so a saved script reloads the same way.
Role names ("humano", "cosa") and the slot ids always work too.

The players of the episode being processed are "active" (`activate`, called when an Episode validates) so every
`assets.character(slot)` lookup returns the player's file. Commands work on one episode at a time.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import cache

from reels import assets
from reels.assets import ROOT

CAST_FILE = ROOT / "reparto.json"

# role -> slot (internal id fixed by the 3D code)
ROLE_SLOTS = {"humano": "novato", "cosa": "claude"}
SLOT_ROLES = {slot: role for role, slot in ROLE_SLOTS.items()}
HUMAN = ROLE_SLOTS["humano"]
THING = ROLE_SLOTS["cosa"]
# Who plays each slot when nobody says otherwise (no reparto.json, or a role left out of it): the template's neutral
# lead and its mug with a face (assets/characters/). A folder named like the slot (a brand pack) wins.
DEFAULT_PLAYERS = {HUMAN: "prota", THING: "taza"}

# Camera presets named after a role (internal names keep the old ids).
CAMERA_ALIASES = {
    "closeup_humano": "closeup_novato",
    "medium_humano_low": "medium_novato_low",
    "mundo_closeup_humano": "mundo_closeup_novato",
    "closeup_cosa": "closeup_ai",
    "mundo_closeup_cosa": "mundo_closeup_ai",
    "cosa_islote": "claude_islote",
}
FIELD_ALIASES = {"humano_fuera": "novato_away"}

_ID = re.compile(r"^[a-z][a-z0-9_]*$")


class CastError(ValueError):
    pass


@dataclass(frozen=True)
class Project:
    aliases: dict[str, str]  # name used in scripts -> internal id (the slot, for role names)
    players: dict[str, str] = field(default_factory=dict)  # slot -> character id that plays it


def _known_ids() -> set[str]:
    return assets.known_characters()


def kind_of(char_id: str) -> str | None:
    """"humano", "cosa" or None (voices off camera, unknown ids): which role a character can play."""
    if char_id in SLOT_ROLES and assets.character_path(char_id) is None:
        return SLOT_ROLES[char_id]  # a slot id with no folder of its own: played by the default player
    try:
        meta = assets.character_file(char_id)
    except FileNotFoundError:
        return None
    if meta.get("offscreen"):
        return None
    role = str(meta.get("role", "")).lower()
    if role in ("humano", "human"):
        return "humano"
    if role in ("cosa", "thing", "ai"):
        return "cosa"
    return "humano" if (meta.get("placeholder") or {}).get("shape") == "human" else "cosa"


def parse_project(data: dict, known_ids: set[str]) -> Project:
    """reparto.json -> aliases and default players. Raises CastError with a plain-language message."""
    aliases: dict[str, str] = {role: slot for role, slot in ROLE_SLOTS.items()}
    players: dict[str, str] = default_players(known_ids)
    wanted: list[tuple[str, str, str, set[str]]] = []
    for role, slot in ROLE_SLOTS.items():
        entry = data.get(role) or {}
        if isinstance(entry, str):  # "cosa": "lucio" is shorthand for {"personaje": "lucio"}
            entry = {"personaje": entry}
        declared = entry.get("interno", slot)
        if declared != slot:
            raise CastError(f'reparto.json "{role}": "interno" es siempre "{slot}" (el hueco del 3D); para que lo '
                            f'interprete otro personaje usa "personaje": "<carpeta en personajes/>"')
        player = entry.get("personaje")
        if player:
            if player not in known_ids:
                raise CastError(f'reparto.json "{role}": el personaje "{player}" no existe (ni en personajes/{player}/ '
                                f'ni en assets/characters/{player}/)')
            players[slot] = player
            if player != slot:
                wanted.append((player, slot, f'"{role}"', {slot, player}))
        name = entry.get("nombre")
        if name:
            wanted.append((name, slot, f'"{role}"', {slot, players[slot]}))
    for name, internal in (data.get("otros") or {}).items():
        if internal not in known_ids:
            raise CastError(f'reparto.json: "otros" usa "{internal}", que no existe en personajes/ ni en assets/characters/')
        wanted.append((name, internal, '"otros"', {internal}))
    for name, internal, where, own in wanted:
        if not _ID.match(name):
            raise CastError(f'reparto.json {where}: el nombre "{name}" solo puede llevar minúsculas sin tildes, '
                            f'números y _ (y empezar por letra), p. ej. "lucia" o "flexo"')
        if name in known_ids and name not in own:
            raise CastError(f'reparto.json {where}: "{name}" ya es otro personaje (tiene su propia carpeta): elige otro nombre')
        if aliases.get(name, internal) != internal:
            raise CastError(f'reparto.json: "{name}" está repetido para dos papeles distintos')
        aliases[name] = internal
    return Project(aliases, players)


def parse(data: dict, known_ids: set[str]) -> dict[str, str]:
    """reparto.json -> {alias: internal id} (kept for callers that only need the names)."""
    return parse_project(data, known_ids).aliases


def default_players(known_ids: set[str]) -> dict[str, str]:
    return {slot: slot if slot in known_ids or DEFAULT_PLAYERS[slot] not in known_ids else DEFAULT_PLAYERS[slot]
            for slot in ROLE_SLOTS.values()}


@cache
def project() -> Project:
    if not CAST_FILE.exists():
        return Project(dict(ROLE_SLOTS), default_players(_known_ids()))
    return parse_project(json.loads(CAST_FILE.read_text(encoding="utf-8")), _known_ids())


def aliases() -> dict[str, str]:
    return project().aliases


aliases.cache_clear = project.cache_clear  # tests clear the project cache through the old name


# --- the episode being processed ------------------------------------------------------------------------------

_active: dict[str, str] = {}


def activate(players: dict[str, str]) -> None:
    """Players of the episode being processed (slot -> character id): character lookups follow them."""
    _active.clear()
    _active.update(players)


def player(char_id: str) -> str:
    """The character folder behind an id: the active player for a slot, the id itself otherwise."""
    return _active.get(char_id) or project().players.get(char_id, char_id)


def resolve(name: str | None, table: dict[str, str] | None = None) -> str | None:
    """A character name as written in a script -> internal id (unknown names pass through for the schema to reject)."""
    if not isinstance(name, str):
        return name
    return (table if table is not None else aliases()).get(name, name)


def script_name(internal: str) -> str:
    """The name the student uses for an internal id (for messages and prompts)."""
    if internal in _active and _active[internal] != internal:
        return _active[internal]
    for name, target in aliases().items():
        if target == internal and name not in ROLE_SLOTS and name != internal:
            return name
    return internal


def cast_for(data: dict) -> tuple[dict[str, str], dict[str, str]]:
    """(aliases, players) for one raw script: project defaults, the script's `reparto`, then inference."""
    proj = project()
    table = dict(aliases())
    players = dict(proj.players)
    known = _known_ids()
    override = data.get("reparto") or {}
    if not isinstance(override, dict):
        raise CastError('"reparto" del guion tiene que ser {"humano": "<personaje>", "cosa": "<personaje>"}')
    for role, who in override.items():
        if role not in ROLE_SLOTS:
            raise CastError(f'"reparto" del guion: el papel "{role}" no existe (solo "humano" y "cosa")')
        slot = ROLE_SLOTS[role]
        target = who if who in known else proj.players.get(table.get(who, ""), table.get(who))
        if not target or target not in known:
            raise CastError(f'"reparto" del guion: "{who}" no es ningún personaje (mira personajes/ y assets/characters/)')
        if kind_of(target) != role:
            raise CastError(f'"reparto" del guion: "{who}" no puede hacer de {role} (es {kind_of(target) or "una voz"})')
        players[slot] = target
        table[who] = slot
    for slot, pid in players.items():
        if pid != slot and table.get(pid, slot) == slot:
            table[pid] = slot
    listed = [c for c in data.get("characters") or [] if isinstance(c, str)]
    taken = {table[c] for c in listed if table.get(c) in SLOT_ROLES} | {c for c in listed if c in SLOT_ROLES}
    for c in listed:
        if c in table or c in SLOT_ROLES:  # a slot id listed as such keeps its (default) player
            continue
        role = kind_of(c)
        slot = ROLE_SLOTS.get(role or "")
        if slot and slot not in taken and role not in override:
            players[slot] = c
            table[c] = slot
            taken.add(slot)
    return table, players


def resolve_script(data: dict) -> dict:
    """Translate a raw script.json dict (as loaded from disk) to internal ids. The file itself is not changed."""
    data = dict(data)
    table, players = cast_for(data)
    if isinstance(data.get("characters"), list):
        data["characters"] = [resolve(c, table) for c in data["characters"]]
        on = set(data["characters"])
        data["reparto"] = {role: players[slot] for role, slot in ROLE_SLOTS.items() if slot in on}
    beats = []
    for beat in data.get("beats") or []:
        if not isinstance(beat, dict):
            beats.append(beat)
            continue
        beat = dict(beat)
        for old, new in FIELD_ALIASES.items():
            if old in beat and new not in beat:
                beat[new] = beat.pop(old)
        for key in ("speaker", "reactor", "gaze"):
            if key in beat:
                beat[key] = resolve(beat[key], table)
        for key in ("camera", "cut_camera"):
            if isinstance(beat.get(key), str):
                beat[key] = CAMERA_ALIASES.get(beat[key], beat[key])
        event = beat.get("event")
        if isinstance(event, dict) and isinstance(event.get("props"), dict) and "owner" in event["props"]:
            beat["event"] = {**event, "props": {**event["props"], "owner": resolve(event["props"]["owner"], table)}}
        beats.append(beat)
    if "beats" in data:
        data["beats"] = beats
    return data
