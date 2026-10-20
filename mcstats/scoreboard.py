"""Read the world scoreboard: AFK times (from the afk-meter datapack) and team name colors."""
from __future__ import annotations

from .config import Config
from .nbt import read_nbt_file


def read(cfg: Config) -> dict:
    try:
        root = read_nbt_file(cfg.world_dir / "data" / "minecraft" / "scoreboard.dat")
    except Exception:
        try:  # older worlds keep it directly in data/
            root = read_nbt_file(cfg.world_dir / "data" / "scoreboard.dat")
        except Exception:
            return {}
    return root.get("data", root)


def afk(cfg: Config, board: dict, online: set[str]) -> dict:
    """AFK seconds per player, measured in-game by the afk-meter datapack.

    The datapack keeps afk_total (seconds AFK), afk_active (seconds active) and afk_idle
    (seconds since the last activity). Minecraft writes the scoreboard on every autosave.
    """
    scores: dict[str, dict[str, int]] = {}
    for e in board.get("PlayerScores", []):
        if str(e.get("Objective", "")).startswith("afk_") and not str(e.get("Name", "")).startswith("#"):
            scores.setdefault(e["Name"], {})[e["Objective"]] = e.get("Score", 0)  # "Score" is omitted when 0
    players = {
        name: {"afk": sc.get("afk_total", 0), "active": sc.get("afk_active", 0),
               "afk_now": name in online and sc.get("afk_idle", 0) >= cfg.afk_threshold}
        for name, sc in scores.items()
    }
    return {"since": cfg.afk_since or None, "players": players}


def team_colors(board: dict) -> dict[str, str]:
    """Name color per player, from the team they are in (e.g. the armor-colors datapack)."""
    return {p: t.get("TeamColor", "white") for t in board.get("Teams", []) for p in t.get("Players", [])}
