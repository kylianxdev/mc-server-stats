"""Read per-player files from the world folder: statistics, advancements and equipment."""
from __future__ import annotations

import json
from pathlib import Path

from .config import Config
from .nbt import read_nbt_file

SLOTS = ("head", "chest", "legs", "feet", "offhand")


def uuid_names(cfg: Config) -> dict[str, str]:
    try:
        return {u["uuid"]: u["name"] for u in json.loads((cfg.minecraft_dir / "usercache.json").read_text())}
    except (OSError, ValueError):
        return {}


def _per_player(folder: Path, pattern: str, names: dict[str, str], reader):
    out = {}
    for f in folder.glob(pattern):
        try:
            out[names.get(f.stem, f.stem[:8])] = reader(f)
        except Exception:  # a file that is being written or is corrupt: skip it this time
            continue
    return out


def load_stats(cfg: Config) -> dict[str, dict]:
    """{player: stats dict} from world/players/stats/<uuid>.json."""
    return _per_player(cfg.world_dir / "players" / "stats", "*.json", uuid_names(cfg),
                       lambda f: json.loads(f.read_text())["stats"])


def advancement_times(cfg: Config) -> dict[str, dict[str, str]]:
    """Per player: {advancement id: when it was completed} (recipes not included).

    Minecraft stores when every criterion was met; the advancement is done at the last one.
    """
    def read(f: Path) -> dict[str, str]:
        d = json.loads(f.read_text())
        return {k.removeprefix("minecraft:"): max(v.get("criteria", {}).values(), default="")[:19]
                for k, v in d.items()
                if isinstance(v, dict) and v.get("done") and not k.startswith("minecraft:recipes/")}
    return _per_player(cfg.world_dir / "players" / "advancements", "*.json", uuid_names(cfg), read)


def advancements_done(times: dict[str, dict[str, str]]) -> dict[str, int]:
    """Number of completed advancements per player (the tab roots don't count)."""
    return {p: sum(1 for k in t if not k.endswith("/root")) for p, t in times.items()}


def _item(it: dict | None) -> dict | None:
    """The parts of an item the website needs (to draw armor and list equipment)."""
    if not it or not it.get("id"):
        return None
    comp = it.get("components", {})
    out = {"id": it["id"].removeprefix("minecraft:")}
    if trim := comp.get("minecraft:trim"):
        out["trim"] = {"material": str(trim.get("material", "")).removeprefix("minecraft:"),
                       "pattern": str(trim.get("pattern", "")).removeprefix("minecraft:")}
    if (color := comp.get("minecraft:dyed_color")) is not None:
        out["color"] = color.get("rgb") if isinstance(color, dict) else color
    if ench := comp.get("minecraft:enchantments"):
        ench = ench.get("levels", ench) if isinstance(ench, dict) else {}
        out["ench"] = {k.removeprefix("minecraft:"): v for k, v in ench.items()}
    return out


def equipment(cfg: Config) -> dict[str, dict]:
    """What every player wears/holds, plus a private count of owned items (inventory, ender chest, shulkers).

    Player files are saved on autosave and when a player logs out; set Paper's
    player-auto-save.rate to e.g. 200 ticks for near real-time updates.
    """
    def read(f: Path) -> dict:
        d = read_nbt_file(f)
        eq = d.get("equipment", {})
        selected = d.get("SelectedItemSlot", 0)
        mainhand = next((i for i in d.get("Inventory", []) if i.get("Slot") == selected), None)
        owned: dict[str, int] = {}

        def walk(items):
            for it in items:
                it = it.get("item", it)  # container entries are {slot, item}
                if it.get("id"):
                    key = it["id"].removeprefix("minecraft:")
                    owned[key] = owned.get(key, 0) + it.get("count", 1)
                    walk(it.get("components", {}).get("minecraft:container", []))

        walk(d.get("Inventory", []))
        walk(d.get("EnderItems", []))
        walk([v for v in eq.values() if isinstance(v, dict)])
        dim = d.get("Dimension", "minecraft:overworld")
        dim = {0: "overworld", -1: "the_nether", 1: "the_end"}.get(dim, dim) if isinstance(dim, int) else str(dim).removeprefix("minecraft:")
        return {**{slot: _item(eq.get(slot)) for slot in SLOTS}, "mainhand": _item(mainhand), "dimension": dim, "owned": owned}

    return _per_player(cfg.world_dir / "players" / "data", "*.dat", uuid_names(cfg), read)


def public_equipment(eq: dict[str, dict]) -> dict[str, dict]:
    """Equipment without the owned-items count: inventories are not published."""
    return {p: {k: v for k, v in g.items() if k != "owned"} for p, g in eq.items()}
