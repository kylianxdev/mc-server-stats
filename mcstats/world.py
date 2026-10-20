"""The state of the world: day number, time of day, weather and the Ender Dragon."""
from __future__ import annotations

from pathlib import Path

from .config import Config
from .nbt import read_nbt_file


def _read(path: Path) -> dict:
    try:
        d = read_nbt_file(path)
        return d.get("data", d.get("Data", d))
    except Exception:
        return {}


def world_state(cfg: Config) -> dict:
    """Read from level.dat and (since Minecraft 26.1) the per-dimension data files."""
    level = _read(cfg.world_dir / "level.dat")
    dims = cfg.world_dir / "dimensions" / "minecraft"
    weather = _read(dims / "overworld" / "data" / "minecraft" / "weather.dat") or level  # older: in level.dat
    dragon = _read(dims / "the_end" / "data" / "minecraft" / "ender_dragon_fight.dat") or level.get("DragonFight", {})
    game_time = level.get("Time") or _read(dims / "overworld" / "data" / "paper" / "level_overrides.dat").get("game_time", 0)
    day_time = level.get("DayTime")  # not stored any more since 26.1 (time of day became a "timeline")
    version = level.get("Version", {})
    return {
        "day": int(game_time // 24000) + 1,
        "time_of_day": int(day_time % 24000) if day_time is not None else None,
        "raining": bool(weather.get("raining", 0)),
        "thundering": bool(weather.get("thundering", 0)),
        "dragon_killed": bool(dragon.get("dragon_killed", dragon.get("DragonKilled", 0)) or dragon.get("previously_killed", dragon.get("PreviouslyKilled", 0))),
        "version": version.get("Name") if isinstance(version, dict) else None,
    }
