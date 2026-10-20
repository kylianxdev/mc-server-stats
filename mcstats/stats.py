"""Fun per-player statistics, computed from Minecraft's own statistics files.

Every statistic has a stable key; the website translates the key and picks an icon.
Values are numbers, except "top" statistics which are {"id": <entity>, "n": <count>}.
"""
from __future__ import annotations


def _cat(st: dict, category: str) -> dict[str, int]:
    return {k.removeprefix("minecraft:"): v for k, v in st.get("minecraft:" + category, {}).items()}


def _total(st, category, match=lambda k: True) -> int:
    return sum(v for k, v in _cat(st, category).items() if match(k))


def _custom(st, *keys) -> int:
    c = _cat(st, "custom")
    return sum(c.get(k, 0) for k in keys)


def _km(st, *keys) -> float:
    return round(_custom(st, *keys) / 100000, 1)


def _top(st, category):
    items = _cat(st, category)
    if not items:
        return None
    k = max(items, key=items.get)
    return {"id": k, "n": items[k]}


CROPS = {"wheat", "carrots", "potatoes", "beetroots", "nether_wart", "melon", "pumpkin", "sugar_cane", "cocoa"}
WALK = ("walk_one_cm", "sprint_one_cm", "crouch_one_cm", "walk_on_water_one_cm", "walk_under_water_one_cm", "climb_one_cm")
RIDE = ("boat_one_cm", "minecart_one_cm", "horse_one_cm", "pig_one_cm", "strider_one_cm", "happy_ghast_one_cm")

# (key, function); the order is the order on the website
STATS = [
    ("blocks_mined", lambda st: _total(st, "mined")),
    ("diamond_ore", lambda st: _total(st, "mined", lambda k: k.endswith("diamond_ore"))),
    ("ancient_debris", lambda st: _total(st, "mined", lambda k: k == "ancient_debris")),
    ("logs_chopped", lambda st: _total(st, "mined", lambda k: k.endswith(("_log", "_stem")))),
    ("saplings_planted", lambda st: _total(st, "used", lambda k: k.endswith(("sapling", "propagule")) or k in ("azalea", "flowering_azalea"))),
    ("crops_harvested", lambda st: _total(st, "mined", lambda k: k in CROPS)),
    ("blocks_used", lambda st: _total(st, "used")),
    ("items_crafted", lambda st: _total(st, "crafted")),
    ("tools_broken", lambda st: _total(st, "broken")),
    ("walked_km", lambda st: _km(st, *WALK)),
    ("swum_km", lambda st: _km(st, "swim_one_cm")),
    ("elytra_km", lambda st: _km(st, "aviate_one_cm")),
    ("ridden_km", lambda st: _km(st, *RIDE)),
    ("jumps", lambda st: _custom(st, "jump")),
    ("mob_kills", lambda st: _custom(st, "mob_kills")),
    ("most_killed", lambda st: _top(st, "killed")),
    ("deaths", lambda st: _custom(st, "deaths")),
    ("killed_by_most", lambda st: _top(st, "killed_by")),
    ("player_kills", lambda st: _custom(st, "player_kills")),
    ("damage_dealt", lambda st: round(_custom(st, "damage_dealt") / 20)),   # stored as 1/10 half-hearts
    ("damage_taken", lambda st: round(_custom(st, "damage_taken") / 20)),
    ("animals_bred", lambda st: _custom(st, "animals_bred")),
    ("fish_caught", lambda st: _custom(st, "fish_caught")),
    ("villager_trades", lambda st: _custom(st, "traded_with_villager")),
    ("items_enchanted", lambda st: _custom(st, "enchant_item")),
    ("chests_opened", lambda st: _custom(st, "open_chest", "open_barrel", "open_shulker_box", "open_enderchest")),
    ("times_slept", lambda st: _custom(st, "sleep_in_bed")),
    ("cake_slices", lambda st: _custom(st, "eat_cake_slice")),
    ("items_dropped", lambda st: _custom(st, "drop")),
]


def fun_stats(stats: dict[str, dict]) -> dict:
    players = sorted(stats)
    return {"players": players,
            "rows": [{"key": key, "values": {p: fn(stats[p]) for p in players}} for key, fn in STATS]}


def playtime(stats: dict[str, dict]) -> dict[str, int]:
    """Total playtime in seconds since the world was created."""
    return {p: _custom(st, "play_time") // 20 for p, st in stats.items()}
