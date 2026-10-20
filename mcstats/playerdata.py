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


def advancements_done(cfg: Config) -> dict[str, int]:
    """Number of completed advancements per player (recipes and tab roots not counted)."""
    def count(f: Path) -> int:
        d = json.loads(f.read_text())
        return sum(1 for k, v in d.items() if isinstance(v, dict) and v.get("done")
                   and not k.startswith("minecraft:recipes/") and not k.endswith("/root"))
    return _per_player(cfg.world_dir / "players" / "advancements", "*.json", uuid_names(cfg), count)


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
        return {**{slot: _item(eq.get(slot)) for slot in SLOTS}, "mainhand": _item(mainhand), "owned": owned}

    return _per_player(cfg.world_dir / "players" / "data", "*.dat", uuid_names(cfg), read)


def public_equipment(eq: dict[str, dict]) -> dict[str, dict]:
    """Equipment without the owned-items count: inventories are not published."""
    return {p: {k: v for k, v in g.items() if k != "owned"} for p, g in eq.items()}
