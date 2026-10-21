"""Demo mode: a made-up survival server, so you can try the website without a Minecraft server.

    python3 -m mcstats --demo

The players wear Minecraft's default skins (Steve, Alex, Noor, ...). All numbers are generated
from a fixed seed, so the demo looks the same every time; it is also used for the screenshots.
"""
from __future__ import annotations

import datetime as dt
import random
from types import SimpleNamespace

from . import __version__
from .config import Config
from .logs import TIME_FMT
from .hall import hall_of_fame
from .progress import progress
from .region import is_surface, valley
from .scoreboard import armor_color
from . import milestones
from .social import pvp
from .stats import fun_stats, ores, playtime

# name: (skin model, how active, how much of a fighter, how much of a builder, equipment)
PLAYERS = {
    "Steve": ("wide", 1.0, 0.8, 1.0, {"head": ("netherite_helmet", "gold", "rib"), "chest": ("netherite_chestplate", "gold", "rib"),
                                      "legs": ("netherite_leggings", "gold", "rib"), "feet": ("netherite_boots", "gold", "rib"),
                                      "mainhand": ("netherite_pickaxe",), "offhand": ("totem_of_undying",)}),
    "Alex": ("slim", 0.9, 1.0, 0.6, {"head": ("diamond_helmet", "amethyst", "wild"), "chest": ("elytra",),
                                     "legs": ("diamond_leggings", "amethyst", "wild"), "feet": ("diamond_boots", "amethyst", "wild"),
                                     "mainhand": ("bow",), "offhand": ("firework_rocket",)}),
    "Noor": ("slim", 0.75, 0.4, 1.2, {"head": ("iron_helmet", "lapis", "coast"), "chest": ("iron_chestplate", "lapis", "coast"),
                                      "legs": ("iron_leggings", "lapis", "coast"), "feet": ("iron_boots", "lapis", "coast"),
                                      "mainhand": ("oak_sapling",)}),
    "Kai": ("wide", 0.6, 1.3, 0.4, {"head": ("diamond_helmet", "redstone", "sentry"), "chest": ("diamond_chestplate", "redstone", "sentry"),
                                    "legs": ("diamond_leggings", "redstone", "sentry"), "feet": ("diamond_boots", "redstone", "sentry"),
                                    "mainhand": ("diamond_sword",), "offhand": ("shield",)}),
    "Makena": ("slim", 0.45, 0.5, 0.8, {"head": ("leather_helmet", None, None, 0x3a6fd8), "chest": ("leather_chestplate", None, None, 0x3a6fd8),
                                        "legs": ("golden_leggings", "emerald", "dune"), "feet": ("chainmail_boots",),
                                        "mainhand": ("fishing_rod",)}),
    "Zuri": ("wide", 0.3, 0.6, 0.5, {"head": ("turtle_helmet",), "chest": ("copper_chestplate",), "mainhand": ("stone_axe",)}),
}
ONLINE = ("Steve", "Noor")
ADVANCEMENTS = [("Stone Age", "task"), ("Getting an Upgrade", "task"), ("Acquire Hardware", "task"), ("Diamonds!", "task"),
                ("We Need to Go Deeper", "task"), ("Hot Stuff", "task"), ("Enchanter", "task"), ("Monster Hunter", "task"),
                ("Sweet Dreams", "task"), ("Hidden in the Depths", "task"), ("Cover Me in Debris", "goal"),
                ("The End?", "task"), ("Free the End", "task"), ("Sky's the Limit", "goal"), ("Hero of the Village", "challenge"),
                ("Return to Sender", "challenge"), ("Serious Dedication", "challenge"), ("A Balanced Diet", "challenge")]
DEATHS = ["was slain by Zombie", "was shot by Skeleton", "fell from a high place", "was blown up by Creeper",
          "tried to swim in lava", "was slain by Enderman", "drowned", "was killed by Witch using magic"]
PVP = {"Steve": ["was slain by Kai"], "Kai": ["was shot by Alex", "was slain by Steve"], "Noor": ["was slain by Kai"]}
DIMENSIONS = {"Alex": "the_nether", "Kai": "the_end"}
# advancement ids per player, most active players got furthest
ADV_IDS = ["story/mine_stone", "story/upgrade_tools", "story/smelt_iron", "story/obtain_armor", "story/lava_bucket", "story/iron_tools",
           "story/deflect_arrow", "story/form_obsidian", "story/mine_diamond", "story/enter_the_nether", "story/shiny_gear",
           "story/enchant_item", "story/cure_zombie_villager", "story/follow_ender_eye", "story/enter_the_end",
           "nether/return_to_sender", "nether/find_fortress", "nether/obtain_blaze_rod", "nether/obtain_ancient_debris",
           "nether/netherite_armor", "nether/brew_potion", "nether/summon_wither", "end/kill_dragon", "end/enter_end_gateway",
           "end/elytra", "adventure/kill_a_mob", "adventure/trade", "adventure/sleep_in_bed", "adventure/shoot_arrow",
           "adventure/totem_of_undying", "adventure/hero_of_the_village", "adventure/adventuring_time", "husbandry/plant_seed",
           "husbandry/breed_an_animal", "husbandry/tame_an_animal", "husbandry/fishy_business", "husbandry/balanced_diet"]
MOBS = ["zombie", "skeleton", "creeper", "spider", "enderman", "witch", "slime", "drowned", "phantom", "piglin",
        "blaze", "wither_skeleton", "pillager", "guardian", "magma_cube", "ghast", "husk", "stray", "cave_spider", "silverfish"]


def _item(spec):
    if not spec:
        return None
    item = {"id": spec[0]}
    if len(spec) > 2 and spec[1]:
        item["trim"] = {"material": spec[1], "pattern": spec[2]}
    if len(spec) > 3:
        item["color"] = spec[3]
    if spec[0].endswith(("_helmet", "_chestplate", "_leggings", "_boots", "_sword", "_pickaxe", "bow")):
        item["ench"] = {"protection": 4, "unbreaking": 3, "mending": 1} if "_" in spec[0] and not spec[0].endswith(("sword", "pickaxe", "bow")) \
            else {"sharpness": 5, "unbreaking": 3, "mending": 1} if spec[0].endswith("sword") \
            else {"efficiency": 5, "fortune": 3, "mending": 1} if spec[0].endswith("pickaxe") else {"power": 5, "infinity": 1}
    return item


def _stats(rng, active, fighter, builder) -> dict:
    hours = 40 * active * rng.uniform(0.85, 1.15)
    kills = {m: int(rng.uniform(5, 140) * fighter * active) for m in rng.sample(MOBS, int(8 + 12 * fighter * active) % len(MOBS) + 1)}
    kills["skeleton"] = int(kills.get("skeleton", 0) + 400 * fighter * active)
    return {
        "minecraft:custom": {
            "minecraft:play_time": int(hours * 3600 * 20),
            "minecraft:walk_one_cm": int(hours * 6_500_000 * rng.uniform(0.8, 1.2)),
            "minecraft:sprint_one_cm": int(hours * 3_000_000), "minecraft:swim_one_cm": int(hours * 200_000 * rng.random()),
            "minecraft:aviate_one_cm": int(hours * 2_000_000) if fighter == 1.0 else 0,
            "minecraft:boat_one_cm": int(hours * 300_000 * rng.random()), "minecraft:jump": int(hours * 1300),
            "minecraft:mob_kills": sum(kills.values()), "minecraft:deaths": int(rng.uniform(4, 9) * active + 2),
            "minecraft:player_kills": rng.randint(0, 2), "minecraft:damage_dealt": int(hours * 5000 * fighter),
            "minecraft:damage_taken": int(hours * 900), "minecraft:animals_bred": int(80 * builder * rng.random()),
            "minecraft:fish_caught": int(60 * rng.random() * (builder > 0.7)), "minecraft:traded_with_villager": int(500 * builder * rng.random()),
            "minecraft:enchant_item": int(30 * active), "minecraft:open_chest": int(hours * 60), "minecraft:sleep_in_bed": int(hours * 1.3),
            "minecraft:eat_cake_slice": rng.randint(0, 12), "minecraft:drop": int(hours * 20),
        },
        "minecraft:mined": {"minecraft:stone": int(hours * 600 * builder), "minecraft:deepslate": int(hours * 300 * active),
                            "minecraft:coal_ore": int(hours * 14), "minecraft:iron_ore": int(hours * 11 * builder),
                            "minecraft:deepslate_iron_ore": int(hours * 5), "minecraft:copper_ore": int(hours * 6),
                            "minecraft:gold_ore": int(hours * 3), "minecraft:redstone_ore": int(hours * 7 * rng.random()),
                            "minecraft:lapis_ore": int(hours * 2), "minecraft:emerald_ore": rng.randint(0, 9),
                            "minecraft:nether_quartz_ore": int(hours * 9 * fighter),
                            "minecraft:diamond_ore": int(60 * active * builder), "minecraft:deepslate_diamond_ore": int(110 * active),
                            "minecraft:ancient_debris": int(24 * active * rng.uniform(0.5, 1.2)), "minecraft:oak_log": int(hours * 70 * builder),
                            "minecraft:wheat": int(hours * 20 * builder)},
        "minecraft:used": {"minecraft:oak_sapling": int(hours * 6 * builder), "minecraft:cobblestone": int(hours * 900 * builder)},
        "minecraft:crafted": {"minecraft:oak_planks": int(hours * 200 * builder), "minecraft:torch": int(hours * 50)},
        "minecraft:broken": {"minecraft:diamond_pickaxe": int(6 * active)},
        "minecraft:killed": {f"minecraft:{m}": n for m, n in kills.items()},
        "minecraft:killed_by": {"minecraft:zombie": 3, "minecraft:skeleton": rng.randint(2, 6), "minecraft:creeper": 2},
    }


def _profile(rng, name, active, now):
    per_day, per_hour, sessions = {}, [0] * 24, 0
    favourite = rng.choice([15, 18, 20])
    for d in range(14):
        day = (now - dt.timedelta(days=13 - d)).strftime("%Y-%m-%d")
        if rng.random() < 0.35 + 0.5 * active:
            secs = int(rng.uniform(0.6, 3.5) * 3600 * active)
            per_day[day] = secs
            sessions += rng.randint(1, 3)
            for i in range(secs // 600):
                per_hour[(favourite + int(rng.gauss(0, 2.2)) + i // 6) % 24] += 600
    first = (now - dt.timedelta(days=13)).strftime("%Y-%m-%d") + " 17:04:12"
    last = (now - dt.timedelta(hours=rng.randint(2, 30))).strftime(TIME_FMT)
    adv = [{"t": (now - dt.timedelta(hours=7 * i + rng.randint(0, 6))).strftime(TIME_FMT), "p": name, "a": a, "kind": k}
           for i, (a, k) in enumerate(rng.sample(ADVANCEMENTS, int(8 + 10 * active)))]
    deaths = [{"t": (now - dt.timedelta(hours=11 * i + 3)).strftime(TIME_FMT), "p": name, "m": m}
              for i, m in enumerate(rng.sample(DEATHS, 4) + PVP.get(name, []))]
    return {"sessions": max(sessions, 1), "longest": int(3600 * rng.uniform(2, 4.5)), "first": first,
            "last": now.strftime(TIME_FMT) if name in ONLINE else last, "per_day": per_day, "per_hour": per_hour,
            "online": name in ONLINE, "advancements": sorted(adv, key=lambda x: x["t"], reverse=True), "deaths": deaths}


def data(cfg: Config) -> dict:
    rng = random.Random(42)
    now = dt.datetime.now().replace(microsecond=0)
    stats, equipment, profiles, colors = {}, {}, {}, {}
    for name, (model, active, fighter, builder, gear) in PLAYERS.items():
        stats[name] = _stats(rng, active, fighter, builder)
        equipment[name] = {slot: _item(gear.get(slot)) for slot in ("head", "chest", "legs", "feet", "mainhand", "offhand")}
        equipment[name]["dimension"] = DIMENSIONS.get(name, "overworld")
        owned = {it["id"]: 1 for it in equipment[name].values() if isinstance(it, dict)}
        equipment[name]["owned"] = owned | {"totem_of_undying": 2, f"{'netherite' if active > 0.8 else 'diamond'}_sword": 1}
        profiles[name] = _profile(rng, name, active, now)
        chest = equipment[name]["chest"]
        colors[name] = armor_color(chest)
    fun = fun_stats(stats)
    adv_times = {}
    for i, (name, (_, active, *_)) in enumerate(PLAYERS.items()):
        # the order of ADV_IDS is the order of the game; more active players get there earlier
        adv_times[name] = {a: (now - dt.timedelta(days=12) + dt.timedelta(hours=6 * j + 9 * i + rng.randint(0, 4))).strftime(TIME_FMT)
                           for j, a in enumerate(ADV_IDS) if rng.random() < active * 0.95 - j * 0.012}
    advancements = {p: len(t) for p, t in adv_times.items()}
    t = lambda h: (now - dt.timedelta(hours=h)).strftime(TIME_FMT)
    commands = [{"t": t(1), "p": "Steve", "c": "/gamerule players_sleeping_percentage 50", "admin": True, "tried": False},
                {"t": t(3), "p": "Kai", "c": "/tp [x y z]", "admin": False, "tried": True},
                {"t": t(5), "p": "Noor", "c": "/seed", "admin": False, "tried": False},
                {"t": t(9), "p": "Alex", "c": "/help", "admin": False, "tried": False},
                {"t": t(30), "p": "Steve", "c": "/whitelist add Zuri", "admin": True, "tried": False}]
    return {
        "generated": now.strftime(TIME_FMT), "first_log": (now - dt.timedelta(days=13)).strftime("%Y-%m-%d"),
        "current_ops": ["Steve"], "ever_ops": ["Steve"], "whitelist": list(PLAYERS),
        "commands": commands, "ops": [{"t": t(300), "p": "Steve", "by": "console", "op": True}],
        "logins": [{"t": t(i * 5 + 1), "p": p} for i, p in enumerate(PLAYERS)],
        "warnings": [{"t": t(40), "m": "Can't keep up! Is the server overloaded? Running 2034ms or 40 ticks behind"}],
        "feedback": [{"t": t(1), "p": "Steve", "m": "Game rule players_sleeping_percentage is now set to 50"}],
        "moderation": [{"t": t(30), "p": "Zuri", "by": "Steve", "a": "whitelist_add"}],
        "profiles": profiles,
        "site": {"title": "Demo Server", "tagline": "a survival world with friends", "default_language": cfg.default_language,
                 "languages": cfg.languages, "show_log": True, "version": __version__},
        "playtime": playtime(stats),
        "fun": fun,
        "afk": {"since": None, "players": {p: {"afk": int(600 * (1 - a) * 3), "active": int(3600 * 9 * a), "afk_now": False}
                                           for p, (_, a, *_) in PLAYERS.items()}},
        "colors": colors,
        "armor": {p: {k: v for k, v in g.items() if k != "owned"} for p, g in equipment.items()},
        "progress": (prog := progress(fun, stats, equipment, advancements, profiles)),
        "world": {"day": 143, "time_of_day": 13200, "raining": False, "thundering": False, "dragon_killed": True, "version": "demo"},
        "advancements": adv_times,
        "hall": hall_of_fame(adv_times, profiles),
        "buddies": [{"a": "Noor", "b": "Steve", "s": 31 * 3600}, {"a": "Alex", "b": "Kai", "s": 19 * 3600},
                    {"a": "Alex", "b": "Steve", "s": 14 * 3600}, {"a": "Makena", "b": "Noor", "s": 8 * 3600},
                    {"a": "Kai", "b": "Zuri", "s": 5 * 3600}],
        "pvp": pvp(profiles),
        "ores": ores(stats),
        "milestones": _milestones(fun, playtime(stats), t),
        "history": _history(prog, playtime(stats), now),
        "skins": {p: {"model": m, "v": "demo"} for p, (m, *_) in PLAYERS.items()},
    }


def _milestones(fun, times, t) -> dict:
    """What the made-up server reached together, the newest a few hours ago."""
    report = milestones.Milestones.report(SimpleNamespace(state=None), fun, times)
    reached = [m for m in report["progress"] if m["reached"]]
    top = milestones.totals(fun, times)
    report["log"] = [{"key": m["key"], "n": m["reached"], "t": t(5 + 17 * i), "top": top[m["key"]][1], "top_n": round(top[m["key"]][2])}
                     for i, m in enumerate(reached[:8])]
    return report


def _history(prog, times, now) -> dict:
    """Three weeks of made-up daily snapshots that grow towards today's numbers."""
    dates = [(now - dt.timedelta(days=20 - i)).strftime("%Y-%m-%d") for i in range(21)]
    rng = random.Random(7)
    series, week = {}, {}
    for p in prog:
        speed = rng.uniform(0.6, 1.4)
        xs = [int(prog[p]["xp"] * (0.35 + 0.65 * (i / 20) ** speed)) for i in range(21)]
        series[p] = {"xp": xs, "playtime": [int(times[p] * (0.4 + 0.6 * i / 20)) for i in range(21)]}
        week[p] = {"xp": xs[-1] - xs[-8], "playtime": int(times[p] * 0.2), "blocks_mined": int(xs[-1] - xs[-8]) * 3,
                   "mob_kills": int((xs[-1] - xs[-8]) / 9), "advancements": rng.randint(1, 5)}
    return {"dates": dates, "series": series, "week": {"since": dates[-8], "players": week}}


def skin_path(cfg: Config, name: str):
    model = PLAYERS.get(name, ("wide",))[0]
    return cfg.assets_dir / "entity" / "player" / model / f"{name.lower()}.png"


def _ground(x: int, z: int) -> int:
    """Height of the made-up land: a valley, low in the middle with hills around it."""
    import math
    return round(2.2 * math.sin(x / 7) + 1.8 * math.cos(z / 8) + 1.2 * math.sin((x + z) / 5) + min(x * x + z * z, 9000) / 260)


def world3d() -> bytes:
    """A small made-up valley for the 3D header: hills, a pond, trees, flowers and everyone's house."""
    import json
    rng = random.Random(3)
    POND, R = 0, 48
    columns: dict[tuple[int, int], dict[int, str]] = {}
    for x in range(-R, R + 1):
        for z in range(-R, R + 1):
            h = _ground(x, z)
            col = {y: "stone" for y in range(h - 6, h - 2)} | {y: "dirt" for y in range(h - 2, h)}
            if (x - 4) ** 2 + (z - 3) ** 2 < 40:  # a pond, its water level flat
                col = {y: v for y, v in col.items() if y < POND - 1} | {POND - 1: "sand"} | ({POND: "water"} if h >= POND else {})
                if h < POND:
                    col.update({h: "sand"} | {y: "water" for y in range(h + 1, POND + 1)})
            else:
                col[h] = "grass_block"
                r = rng.random()
                if r < 0.10:
                    col[h + 1] = "short_grass"
                elif r < 0.13:
                    col[h + 1] = rng.choice(["poppy", "dandelion", "cornflower", "oxeye_daisy", "allium"])
            columns[(x, z)] = col
    ground = lambda x, z: max(y for y, n in columns[(x, z)].items() if n in ("grass_block", "water", "sand", "dirt"))

    def house(hx, hz, wall, roof):  # a 7×7 house with a door, windows and a pitched roof; returns the bed
        floor = max(ground(hx + dx, hz + dz) for dx in range(-3, 4) for dz in range(-3, 4))
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                col = columns[(hx + dx, hz + dz)]
                for y in [y for y in col if y > floor]:
                    del col[y]
                for y in range(ground(hx + dx, hz + dz), floor + 1):
                    col[y] = "cobblestone"
                edge = abs(dx) == 3 or abs(dz) == 3
                for y in range(floor + 1, floor + 4):
                    if edge:
                        corner = abs(dx) == 3 and abs(dz) == 3
                        window = y == floor + 2 and not corner and (dx == 0 or dz == 0) and not (dz == 3 and dx == 0)
                        door = dz == 3 and dx == 0 and y < floor + 3
                        if not door:
                            col[y] = "oak_log" if corner else "glass" if window else wall
                roof_y = floor + 4 + (2 - min(abs(dz), 2)) if abs(dz) < 3 else floor + 4
                col[roof_y] = roof
        columns[(hx, hz - 1)][floor + 1] = "red_wool"
        return (hx, floor + 1, hz - 1)

    homes = {"Steve": house(-17, -12, "oak_planks", "spruce_planks"), "Alex": house(19, -15, "birch_planks", "dark_oak_planks"),
             "Noor": house(-14, 17, "stone_bricks", "spruce_planks"), "Kai": house(20, 16, "spruce_planks", "bricks")}
    for tx, tz in [(-30, 6), (11, 30), (-28, -27), (31, -2), (-3, -30), (34, 33), (-36, 30), (3, 38)]:  # oak trees
        h = ground(tx, tz)
        for dy in range(1, 6):
            columns[(tx, tz)][h + dy] = "oak_log"
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(4, 8):
                    if abs(dx) + abs(dz) + max(0, dy - 6) * 2 <= 3 and (dx or dz or dy > 5) and (tx + dx, tz + dz) in columns:
                        columns[(tx + dx, tz + dz)].setdefault(h + dy, "oak_leaves")

    def top(x, z):
        if (x, z) not in columns:  # the hills further away
            return _ground(x, z)
        ys = [y for y, n in columns[(x, z)].items() if is_surface(n)]
        return max(ys) if ys else None

    def block(x, y, z):
        if (x, z) not in columns:
            return ("grass_block" if y == _ground(x, z) else "air"), {}
        return columns[(x, z)].get(y, "air"), {}
    return json.dumps(valley(top, block, (0, 0), homes, margin=12, max_half=R - 4, far=160), separators=(",", ":")).encode()


def live3d() -> dict[str, list[float]]:
    """Where the online demo players are right now: Steve walks between his house and the pond, Noor is at home."""
    import math
    import time
    path = [(-17, -8), (-8, -4), (0, -3), (-2, 8), (-12, 9), (-20, 0)]
    t = time.time() / 4 % len(path)  # 4 seconds from point to point
    (ax, az), (bx, bz) = path[int(t)], path[(int(t) + 1) % len(path)]
    f = t - int(t)
    x, z = ax + (bx - ax) * f, az + (bz - az) * f
    yaw = math.degrees(math.atan2(-(bx - ax), bz - az))
    return {"Steve": [round(x, 1), _ground(round(x), round(z)) + 1, round(z, 1), round(yaw)],
            "Noor": [-14.5, _ground(-14, 22) + 1, 22.5, 180]}
