"""Demo mode: a made-up survival server, so you can try the website without a Minecraft server.

    python3 -m mcstats --demo

The players wear Minecraft's default skins (Steve, Alex, Noor, ...). All numbers are generated
from a fixed seed, so the demo looks the same every time; it is also used for the screenshots.
"""
from __future__ import annotations

import datetime as dt
import random

from . import __version__
from .config import Config
from .logs import TIME_FMT
from .progress import progress
from .stats import fun_stats, playtime

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
TRIM_COLOR = {"amethyst": "light_purple", "copper": "red", "diamond": "aqua", "emerald": "green", "gold": "yellow", "iron": "gray",
              "lapis": "blue", "netherite": "dark_purple", "quartz": "white", "redstone": "dark_red", "resin": "gold"}
CHEST_COLOR = {"leather": "gold", "copper": "red", "chainmail": "dark_gray", "iron": "gray", "golden": "yellow",
               "diamond": "aqua", "netherite": "dark_purple"}
ADVANCEMENTS = [("Stone Age", "task"), ("Getting an Upgrade", "task"), ("Acquire Hardware", "task"), ("Diamonds!", "task"),
                ("We Need to Go Deeper", "task"), ("Hot Stuff", "task"), ("Enchanter", "task"), ("Monster Hunter", "task"),
                ("Sweet Dreams", "task"), ("Hidden in the Depths", "task"), ("Cover Me in Debris", "goal"),
                ("The End?", "task"), ("Free the End", "task"), ("Sky's the Limit", "goal"), ("Hero of the Village", "challenge"),
                ("Return to Sender", "challenge"), ("Serious Dedication", "challenge"), ("A Balanced Diet", "challenge")]
DEATHS = ["was slain by Zombie", "was shot by Skeleton", "fell from a high place", "was blown up by Creeper",
          "tried to swim in lava", "was slain by Enderman", "drowned", "was killed by Witch using magic"]
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
              for i, m in enumerate(rng.sample(DEATHS, 4))]
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
        owned = {it["id"]: 1 for it in equipment[name].values() if it}
        equipment[name]["owned"] = owned | {"totem_of_undying": 2, f"{'netherite' if active > 0.8 else 'diamond'}_sword": 1}
        profiles[name] = _profile(rng, name, active, now)
        chest = equipment[name]["chest"]
        colors[name] = (TRIM_COLOR[chest["trim"]["material"]] if chest and chest.get("trim")
                        else CHEST_COLOR.get(chest["id"].split("_")[0], "white") if chest and chest["id"].endswith("_chestplate") else "white")
    fun = fun_stats(stats)
    advancements = {p: len(pr["advancements"]) + 6 for p, pr in profiles.items()}
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
        "progress": progress(fun, stats, equipment, advancements, profiles),
        "skins": {p: {"model": m, "v": "demo"} for p, (m, *_) in PLAYERS.items()},
    }


def skin_path(cfg: Config, name: str):
    model = PLAYERS.get(name, ("wide",))[0]
    return cfg.assets_dir / "entity" / "player" / model / f"{name.lower()}.png"
