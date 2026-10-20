"""The "site level": points (site XP) for what a player achieved, NOT for how long they played.

Every category has a weight (how relevant it is) and a cap, so a single thing — crafting
80,000 items or farming 2,000 skeletons — can't decide everything. The level uses the real
Minecraft experience formula, so the numbers feel familiar.
"""
from __future__ import annotations

# (key, site XP per unit, cap) — keys are stat keys from stats.py, plus "advancements" and "distance_km"
WEIGHTS = [
    ("advancements", 60, None),
    ("diamond_ore", 6, 1500),
    ("ancient_debris", 25, 1000),
    ("blocks_mined", 0.04, 1500),
    ("blocks_used", 0.03, 1500),
    ("items_crafted", 0.015, 1000),
    ("logs_chopped", 0.15, 800),
    ("saplings_planted", 0.8, 500),
    ("crops_harvested", 0.3, 500),
    ("player_kills", 20, 400),
    ("animals_bred", 1.5, 500),
    ("villager_trades", 0.6, 1200),
    ("items_enchanted", 6, 600),
    ("fish_caught", 2, 400),
    ("distance_km", 4, 1000),
]
DISTANCE = ("walked_km", "swum_km", "elytra_km", "ridden_km")

# mob kills: variety counts, farming hundreds of the same mob doesn't go on forever
MOB_PER_KILL, MOB_KILLS_PER_TYPE, MOB_PER_TYPE, MOB_CAP = 0.5, 40, 15, 1500

# worn armor per piece (netherite = ancient debris + gold + a diamond piece + a smithing template)
ARMOR = {"netherite": 300, "diamond": 100, "iron": 30, "copper": 20, "chainmail": 20, "golden": 15, "leather": 5, "turtle": 40}
TRIM, PER_ENCHANT_LEVEL = 40, 4
# best tool of each kind a player owns (inventory, ender chest, shulker boxes)
TOOL = {"netherite": 150, "diamond": 50, "iron": 10}
TOOLS = ("sword", "pickaxe", "axe", "shovel", "hoe")
SPECIAL = {"elytra": (400, 1), "trident": (150, 1), "mace": (250, 1), "totem_of_undying": (30, 3)}  # (points, max count)
# extra for rare advancements (kind taken from the chat message in the logs)
CHALLENGE, GOAL = 100, 40


def mc_level(xp: float) -> tuple[int, float]:
    """Level and progress towards the next level, using Minecraft's experience formula."""
    def total(level: int) -> float:
        if level <= 16:
            return level * level + 6 * level
        if level <= 31:
            return 2.5 * level * level - 40.5 * level + 360
        return 4.5 * level * level - 162.5 * level + 2220

    level = 0
    while total(level + 1) <= xp:
        level += 1
    return level, (xp - total(level)) / (total(level + 1) - total(level))


def gear_points(gear: dict) -> int:
    pts = 0
    for slot in ("head", "chest", "legs", "feet"):
        it = gear.get(slot)
        if not it:
            continue
        pts += next((v for prefix, v in ARMOR.items() if it["id"].startswith(prefix)), 0)
        pts += TRIM if it.get("trim") else 0
        pts += PER_ENCHANT_LEVEL * sum((it.get("ench") or {}).values())
    owned = gear.get("owned", {})
    for tool in TOOLS:
        pts += max((v for mat, v in TOOL.items() if owned.get(f"{mat}_{tool}")), default=0)
    for item, (v, most) in SPECIAL.items():
        pts += v * min(owned.get(item, 0), most)
    return pts


def mob_variety_points(killed: dict[str, int]) -> int:
    return round(min(sum(MOB_PER_KILL * min(n, MOB_KILLS_PER_TYPE) + MOB_PER_TYPE for n in killed.values()), MOB_CAP))


def progress(fun: dict, stats: dict[str, dict], equipment: dict[str, dict],
             advancements: dict[str, int], profiles: dict[str, dict]) -> dict[str, dict]:
    rows = {r["key"]: r["values"] for r in fun["rows"]}
    out = {}
    for p in fun["players"]:
        def value(key):
            if key == "advancements":
                return advancements.get(p, 0)
            if key == "distance_km":
                return sum(rows[k].get(p, 0) for k in DISTANCE)
            v = rows.get(key, {}).get(p, 0)
            return v if isinstance(v, (int, float)) else 0

        parts = []
        for key, weight, cap in WEIGHTS:
            pts = value(key) * weight
            parts.append([key, round(min(pts, cap) if cap else pts)])
        killed = {k.removeprefix("minecraft:"): v for k, v in stats.get(p, {}).get("minecraft:killed", {}).items()}
        parts.append(["mob_variety", mob_variety_points(killed)])
        parts.append(["gear", gear_points(equipment.get(p, {}))])
        kinds = [a["kind"] for a in profiles.get(p, {}).get("advancements", [])]
        parts.append(["hard_advancements", CHALLENGE * kinds.count("challenge") + GOAL * kinds.count("goal")])

        xp = sum(v for _, v in parts)
        level, frac = mc_level(xp)
        out[p] = {"xp": xp, "level": level, "frac": round(frac, 3),
                  "parts": sorted(parts, key=lambda x: -x[1]), "advancements": advancements.get(p, 0)}
    return out
