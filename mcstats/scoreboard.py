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


# the same rules as the armor-colors datapack: the trim color wins, otherwise the chestplate material
TRIM_COLOR = {"amethyst": "light_purple", "copper": "red", "diamond": "aqua", "emerald": "green", "gold": "yellow", "iron": "gray",
              "lapis": "blue", "netherite": "dark_purple", "quartz": "white", "redstone": "dark_red", "resin": "gold"}
CHEST_COLOR = {"leather": "gold", "copper": "red", "chainmail": "dark_gray", "iron": "gray", "golden": "yellow",
               "diamond": "aqua", "netherite": "dark_purple"}


def armor_color(chest: dict | None) -> str:
    """Name color for a chestplate (an item dict with "id" and maybe "trim")."""
    if not chest or not chest.get("id", "").endswith("_chestplate"):
        return "white"
    if chest.get("trim"):
        return TRIM_COLOR.get(chest["trim"].get("material", ""), "white")
    return CHEST_COLOR.get(chest["id"].split("_")[0], "white")


def name_colors(board: dict, armor: dict) -> dict[str, str]:
    """Name color of every player: their team when the datapack has seen them, otherwise their saved armor.

    The datapack only sorts players who are online, so players who haven't joined since it was added
    have no team yet.
    """
    return {p: armor_color(eq.get("chest")) for p, eq in armor.items()} | team_colors(board)


def team_colors(board: dict) -> dict[str, str]:
    """Name color per player, from the team they are in (e.g. the armor-colors datapack)."""
    return {p: t.get("TeamColor", "white") for t in board.get("Teams", []) for p in t.get("Players", [])}
